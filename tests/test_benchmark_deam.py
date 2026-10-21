"""Synthetic offline checks for DEAM benchmark; never downloads dataset audio."""
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
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("benchmark_deam", SCRIPTS / "benchmark_deam.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class DeamBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.annotation_zip = self.root / "annotations.zip"
        self.audio_zip = self.root / "audio.zip"
        self.db = self.root / "synthetic.db"
        with zipfile.ZipFile(self.annotation_zip, "w") as archive:
            rows = io.StringIO(newline="")
            writer = csv.writer(rows)
            writer.writerow(("song_id", " valence_mean", "arousal_mean", "valence_std"))
            for i in range(1, 9):
                writer.writerow((i, 1 + i * 0.75, 1 + i * 0.75, .4))
            archive.writestr(
                "DEAM_Annotations/annotations/annotations averaged per song/"
                "song_level/static_annotations_averaged_songs_1_2000.csv",
                rows.getvalue(),
            )
        with zipfile.ZipFile(self.audio_zip, "w") as archive:
            for i in range(1, 9):
                archive.writestr(f"DEAM_audio/MEMD_audio/{i}.mp3", b"f" * 2048)
        self.create_db()

    def create_db(self):
        with closing(sqlite3.connect(self.db)) as connection:
            connection.executescript("""
                PRAGMA user_version=3;
                CREATE TABLE feature_models (
                    model_key TEXT PRIMARY KEY,
                    preprocessing_version TEXT NOT NULL,
                    aggregation TEXT NOT NULL,
                    classes_json TEXT NOT NULL,
                    validated_against_essentia INTEGER NOT NULL
                );
                CREATE TABLE feature_tracks (
                    track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                    capability TEXT NOT NULL, model_key TEXT NOT NULL,
                    scores_f32_le BLOB NOT NULL,
                    PRIMARY KEY(track_file,model_id)
                );
            """)
            for head, (capability, count) in bench.ev.MODELS.items():
                connection.execute("INSERT INTO feature_models VALUES(?,?,?,?,0)", (
                    f"deam-{head}", "experimental-essentia-audio-v5-f32-src-ratio-unvalidated",
                    bench.ev.AGGREGATION,
                    json.dumps([f"{head}_{k}" for k in range(count)]),
                ))
                for i in range(1, 9):
                    vector = [0.005 + k * 0.00001 for k in range(count)]
                    vector[0] = 0.1 + i * 0.07
                    vector[1] = 0.9 - i * 0.07
                    connection.execute(
                        "INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                        (f"DEAM/{i}.mp3", head, capability, f"deam-{head}",
                         struct.pack("<" + "f" * count, *vector)),
                    )
            connection.commit()

    def test_metadata_and_audio_matching(self):
        labels = bench.load_annotations(self.annotation_zip)
        mp3s = bench.match_audio(self.audio_zip, labels)
        self.assertEqual(len(labels), 8)
        self.assertEqual(len(mp3s), 8)
        self.assertEqual(labels["1"], (1.75, 1.75))
        a = bench.select_ids(labels, mp3s, 6, 20261021)
        self.assertEqual(a, bench.select_ids(labels, mp3s, 6, 20261021))
        self.assertEqual(len(set(a)), 6)

    def test_evaluate_is_read_only_and_no_track_scores_in_report(self):
        source_before = self.db.read_bytes()
        annotations = bench.load_annotations(self.annotation_zip)
        ids = bench.select_ids(annotations, bench.match_audio(self.audio_zip, annotations), 8, 42)
        result = bench.evaluate(self.db, ids, annotations, 42)
        self.assertEqual(self.db.read_bytes(), source_before)
        self.assertEqual(result["dataset"]["songs_evaluated"], 8)
        self.assertEqual(set(result["per_head"]), {"genre", "moodtheme"})
        for head in bench.ev.MODELS:
            self.assertEqual(set(result["per_head"][head]), set(bench.ev.METRICS))
            for metric in bench.ev.METRICS:
                axis = result["per_head"][head][metric]["axes"]["valence_arousal"]
                self.assertEqual(axis["query_count"], 8)
                self.assertIsNotNone(axis["mean_query_spearman"])
                self.assertEqual(len(axis["query_bootstrap_95pct"]), 2)
        serialized = json.dumps(result)
        self.assertNotIn("DEAM/1.mp3", serialized)
        self.assertNotIn("scores_f32_le", serialized)

    def test_missing_vectors_fail_not_silently_skipped(self):
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute(
                "DELETE FROM feature_tracks WHERE track_file=? AND model_id=?",
                ("DEAM/1.mp3", "genre"),
            )
            connection.commit()
        with self.assertRaisesRegex(ValueError, "Missing compatible"):
            bench.evaluate(self.db, [str(i) for i in range(1, 9)],
                           bench.load_annotations(self.annotation_zip), 0)

    def test_duplicate_audio_rejected(self):
        with zipfile.ZipFile(self.audio_zip, "a") as archive:
            archive.writestr("another/path/1.mp3", b"f" * 2048)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            bench.match_audio(self.audio_zip, bench.load_annotations(self.annotation_zip))

    def test_duplicate_conflicting_labels_rejected(self):
        with zipfile.ZipFile(self.annotation_zip, "a") as archive:
            archive.writestr(
                "a/static_annotations_averaged_songs_2001_2058.csv",
                "song_id,valence_mean,arousal_mean\n1,9,9\n",
            )
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            bench.load_annotations(self.annotation_zip)

    def test_rank_ties_and_constant_reject(self):
        self.assertEqual(bench.average_ranks([10, 10, 15]), [1.5, 1.5, 3])
        self.assertEqual(bench.spearman([1, 2, 3], [3, 2, 1]), -1.)
        self.assertIsNone(bench.spearman([1, 1, 1], [3, 2, 1]))

    def test_no_overwrite_inference(self):
        with self.assertRaises(FileExistsError):
            bench.run_inference(self.root / "missing", self.root, self.audio_zip,
                                ["1"], {"1": "1.mp3"}, self.db)


if __name__ == "__main__":
    unittest.main()
