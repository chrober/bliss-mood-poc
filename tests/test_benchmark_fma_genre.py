"""Synthetic FMA-Small artist-distinct genre retrieval benchmark checks."""
import csv
from contextlib import closing
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("benchmark_fma_genre", SCRIPTS / "benchmark_fma_genre.py")
fma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fma)


class FmaGenreBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meta = self.root / "metadata.zip"
        self.audio = self.root / "audio.zip"
        self.database = self.root / "features.db"
        self.genres = ["Rock", "Pop", "Electronic", "Hip-Hop", "Experimental",
                       "Instrumental", "International", "Folk"]
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["", "set", "set", "track", "artist"])
        writer.writerow(["", "subset", "split", "genre_top", "id"])
        with zipfile.ZipFile(self.audio, "w") as audio:
            for genre_id, genre in enumerate(self.genres):
                for track_offset in (0, 1):
                    track_id = genre_id * 10 + track_offset + 101
                    writer.writerow([
                        str(track_id), "small", "validation", genre,
                        str(track_id),
                    ])
                    audio.writestr(
                        f"fma_small/{track_id // 1000:03d}/{track_id:06d}.mp3",
                        b"f" * 16000,
                    )
        with zipfile.ZipFile(self.meta, "w") as metadata:
            metadata.writestr("fma_metadata/tracks.csv", buffer.getvalue())
        self.create_db()

    def create_db(self):
        with closing(sqlite3.connect(self.database)) as conn:
            conn.executescript("""
                PRAGMA user_version=3;
                CREATE TABLE feature_models (
                    model_key TEXT PRIMARY KEY,
                    preprocessing_version TEXT NOT NULL,
                    aggregation TEXT NOT NULL,
                    classes_json TEXT NOT NULL,
                    validated_against_essentia INTEGER NOT NULL
                );
                CREATE TABLE feature_tracks (
                    track_file TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    model_key TEXT NOT NULL,
                    scores_f32_le BLOB NOT NULL,
                    PRIMARY KEY(track_file,model_id)
                );
            """)
            count = fma.ev.MODELS["genre"][1]
            conn.execute("INSERT INTO feature_models VALUES(?,?,?,?,0)", (
                "genre-fma-v5", "experimental-essentia-audio-v5-f32-src-ratio-unvalidated",
                fma.ev.AGGREGATION, json.dumps([f"class_{i}" for i in range(count)]),
            ))
            for idx in range(8):
                for off in (0, 1):
                    ident = idx * 10 + off + 101
                    values = [0.005 + j * 0.00001 for j in range(count)]
                    values[idx] = .8 - off * .02
                    values[(idx + 1) % count] = .2 + off * .02
                    conn.execute("INSERT INTO feature_tracks VALUES(?,?,?,?,?)", (
                        f"FMA/{ident:06d}.mp3", "genre", "genre",
                        "genre-fma-v5", struct.pack("<" + "f" * count, *values),
                    ))
            conn.commit()

    def test_small_metadata_and_balanced_artist_selection(self):
        tracks = fma.load_fma_small(self.meta)
        audio = fma.match_audio(self.audio, tracks)
        selected = fma.balanced_sample(tracks, audio, "validation", 2, 20261021)
        self.assertEqual(selected, fma.balanced_sample(
            tracks, audio, "validation", 2, 20261021))
        self.assertEqual(len(selected), 16)
        self.assertEqual(len({tracks[i]["artist"] for i in selected}), 16)
        self.assertEqual(len({tracks[i]["genre"] for i in selected}), 8)
        with self.assertRaisesRegex(ValueError, "Only non-test"):
            fma.balanced_sample(tracks, audio, "test", 2, 20261021)

    def test_all_seven_metrics_aggregate_without_editing_sqlite(self):
        tracks = fma.load_fma_small(self.meta)
        ids = fma.balanced_sample(
            tracks, fma.match_audio(self.audio, tracks), "validation", 2, 20261021
        )
        before = self.database.read_bytes()
        report = fma.evaluate(self.database, ids, tracks, 20261021, "validation")
        self.assertEqual(self.database.read_bytes(), before)
        self.assertEqual(report["dataset"]["sample_size"], 16)
        self.assertEqual(report["dataset"]["official_split"], "validation")
        self.assertEqual(report["dataset"]["distinct_artists"], 16)
        self.assertEqual(len(report["metric_results"]), 7)
        self.assertAlmostEqual(report["baseline_random_precision_at_5"], 1/15)
        for name, metric in report["metric_results"].items():
            with self.subTest(name=name):
                n = metric["precision_at_5"]["query_count"]
                if n == 0:
                    # The historical absolute-cutoff Top-K may legitimately
                    # have no eligible positive-overlap neighbors at all.
                    self.assertIsNone(metric["precision_at_5"]["macro_mean"])
                    self.assertEqual(metric["queries_insufficient_candidates"], 16)
                else:
                    self.assertTrue(0 <= metric["precision_at_5"]["macro_mean"] <= 1)
                    self.assertTrue(0 <= metric["map_at_10"]["macro_mean"] <= 1)
                    self.assertTrue(0 <= metric["ndcg_at_10"]["macro_mean"] <= 1)
                    self.assertEqual(n, 16)
        serialized = json.dumps(report)
        self.assertNotIn("FMA/000101.mp3", serialized)
        self.assertNotIn('"101"', serialized)

    def test_anomalous_mp3_is_excluded_without_failing_entire_zip(self):
        songs = fma.load_fma_small(self.meta)
        original_id = next(iter(songs))
        with zipfile.ZipFile(self.audio, "a") as archive:
            archive.writestr(
                "fma_small/000/000999.mp3", b"not a sampled song"
            )
        found = fma.match_audio(self.audio, songs)
        self.assertEqual(len(found), 16)
        with zipfile.ZipFile(self.audio, "w") as archive:
            for ident in songs:
                archive.writestr(f"fma_small/{ident}.mp3",
                                 b"x" * (100 if ident == original_id else 16000))
        found = fma.match_audio(self.audio, songs)
        self.assertEqual(len(found), 15)
        self.assertNotIn(original_id, found)

    def test_excessive_anomalies_fail_closed(self):
        songs = fma.load_fma_small(self.meta)
        with zipfile.ZipFile(self.audio, "w") as archive:
            for ident in songs:
                archive.writestr(f"fma_small/{ident}.mp3", b"tiny")
        with self.assertRaisesRegex(ValueError, "Too few valid|Too many anomalous"):
            fma.match_audio(self.audio, songs)

    def test_zero_overlap_is_not_invented_as_neighbor(self):
        p, ap, ndcg = fma._retrieval([False, False, True, True, False], 2, 5)
        self.assertEqual(p, .4)
        self.assertGreater(ap, 0)
        self.assertGreater(ndcg, 0)

    def test_rejects_incomplete_genre_sample(self):
        tracks = fma.load_fma_small(self.meta)
        available = fma.match_audio(self.audio, tracks)
        one = next(k for k in tracks if tracks[k]["genre"] == "Folk")
        del available[one]
        with self.assertRaisesRegex(ValueError, "Not enough independent artists"):
            fma.balanced_sample(tracks, available, "validation", 2, 1)


if __name__ == "__main__":
    unittest.main()
