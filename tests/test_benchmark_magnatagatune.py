"""Offline regression tests for MTT sparse multi-part audio and triplet scoring."""
from contextlib import closing
import csv
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import struct
import zlib
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("benchmark_mtt", ROOT / "benchmark_magnatagatune.py")
mtt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mtt)


class SparseMttBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.comparisons = self.root / "comparisons.csv"
        self.clips = self.root / "clips.csv"
        self.tail = self.root / "tail.bin"
        self.db = self.root / "bench.db"
        source = io.StringIO(newline="")
        wr = csv.writer(source)
        wr.writerow(mtt.COMPARISON_FIELDS)
        for question in range(4):
            ids = [str(question * 3 + off) for off in (1, 2, 3)]
            wr.writerow([*ids, "8", "1", "1", *(f"{item}.mp3" for item in ids)])
        self.comparisons.write_text(source.getvalue(), encoding="utf-8")
        source = io.StringIO(newline="")
        wr = csv.writer(source)
        wr.writerow(["clip_id", "track_number", "title", "artist", "album",
                     "url", "segmentStart", "segmentEnd", "original_url", "mp3_path"])
        for ident in range(1, 13):
            wr.writerow([ident, ident, f"Track {ident}", f"Artist {ident}",
                         "Album", "url", 0, 30, "orig", f"{ident}.mp3"])
        self.clips.write_text(source.getvalue(), encoding="utf-8")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for ident in range(1, 130):
                archive.writestr(f"mp3/{ident}.mp3",
                                 b"ID3" + bytes([ident % 251]) * 3000)
        self.archive_bytes = output.getvalue()
        n = len(self.archive_bytes)
        self.sizes = [n // 12, n // 12, n - 2 * (n // 12)]
        self.tail.write_bytes(self.archive_bytes[-min(self.sizes[2], 18000):])
        self.models()

    def models(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.executescript("""
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
            for head, (capability, dims) in mtt.ev.MODELS.items():
                db.execute("INSERT INTO feature_models VALUES(?,?,?,?,0)",
                           (f"mtt-{head}", "experimental-essentia-audio-v5-f32-src-ratio-unvalidated",
                            mtt.ev.AGGREGATION,
                            json.dumps([f"{head}_{j}" for j in range(dims)])))
                for ident in range(1, 13):
                    values = [0.00001] * dims
                    values[0] = .1 + .05 * ident
                    values[1] = .9 - .05 * ident
                    db.execute("INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                               (f"MTT/{ident}.mp3", head, capability, f"mtt-{head}",
                                struct.pack("<" + "f" * dims, *values)))
            db.commit()

    def test_artist_disjoint_high_consensus_sampling(self):
        groups, cat = mtt.triplets_by_vote(self.comparisons, self.clips)
        chosen = mtt.dev_selection(groups, cat, count=4, seed=20261021)
        self.assertEqual(chosen, mtt.dev_selection(groups, cat, 4, 20261021))
        self.assertEqual(len({i for t in chosen for i in t}), 12)
        self.assertEqual(len({cat[i]["artist"] for t in chosen for i in t}), 12)
        self.assertEqual(mtt.dev_selection(groups, cat, 2, 20261021).__len__(), 2)

    def test_sparse_remote_zip_crc_decode_and_cross_part_range(self):
        members, _ = mtt.directory.zip_member_directory(self.tail, self.sizes)
        class InMemoryFetcher(mtt.RangeFetcher):
            def _part_range(inner, part, start, end):
                position = sum(self.sizes[:part-1]) + start
                data = self.archive_bytes[position:position + (end-start+1)]
                inner.total_bytes += len(data)
                inner.requests += 1
                return data
        getter = InMemoryFetcher(self.sizes)
        for ident in ("1", "7", "12"):
            info = mtt.member_lookup(members, f"{ident}.mp3")
            data = mtt.extract_mp3(info, getter)
            self.assertEqual(data[:3], b"ID3")
            self.assertEqual(len(data), 3003)
        self.assertGreater(getter.requests, 0)
        self.assertLess(getter.total_bytes, len(self.archive_bytes))

    def test_bad_remote_payload_crc_rejected(self):
        members, _ = mtt.directory.zip_member_directory(self.tail, self.sizes)
        class DamagedFetcher(mtt.RangeFetcher):
            def _part_range(inner, part, start, end):
                position = sum(self.sizes[:part-1]) + start
                payload = bytearray(self.archive_bytes[position:position+end-start+1])
                # Damage compressed bytes of some fetch ranges.
                if len(payload) > 45:
                    name_len, extra_len = struct.unpack_from("<HH", payload, 26)
                    first_compressed = 30 + name_len + extra_len
                    if first_compressed + 2 < len(payload):
                        payload[first_compressed + 2] ^= 1
                return bytes(payload)
        getter = DamagedFetcher(self.sizes)
        with self.assertRaises((ValueError, zlib.error)):
            mtt.extract_mp3(mtt.member_lookup(members, "1.mp3"), getter)

    def test_frozen_128_artist_partition_excludes_holdout_from_audio_selection(self):
        import audit_magnatagatune_holdout as holdout

        artists_dev = [f"FrozenDev {i}" for i in range(200)
                       if holdout.artist_bucket(f"frozendev {i}") == "development"][:12]
        artists_hold = [f"FrozenHold {i}" for i in range(200)
                        if holdout.artist_bucket(f"frozenhold {i}") == "holdout"][:3]
        self.assertEqual((len(artists_dev), len(artists_hold)), (12, 3))
        with self.clips.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["clip_id", "track_number", "title", "artist", "album",
                             "url", "segmentStart", "segmentEnd", "original_url", "mp3_path"])
            for ident, artist in enumerate(artists_dev + artists_hold, 1):
                writer.writerow([ident, ident, f"Track {ident}", artist, "Album",
                                 "url", 0, 30, "orig", f"{ident}.mp3"])
        with self.comparisons.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(mtt.COMPARISON_FIELDS)
            for first in (1, 4, 7, 10, 13):
                ids = [str(i) for i in (first, first + 1, first + 2)]
                writer.writerow([*ids, 8, 1, 1, *(f"{ident}.mp3" for ident in ids)])

        groups, catalog = mtt.triplets_by_vote(self.comparisons, self.clips)
        selected, proof = mtt.frozen_artist_development_selection(groups, catalog)
        self.assertEqual(len(selected), 4)
        self.assertEqual(proof["holdout_triplets_never_scored"], 1)
        self.assertEqual(proof["mixed_triplets_excluded"], 0)
        self.assertNotIn(("13", "14", "15"), selected)
        for triple in selected:
            self.assertTrue(all(holdout.artist_bucket(catalog[i]["artist"], 128)
                                == "development" for i in triple))
        self.assertEqual(proof["development_partition_sha256"],
                         holdout.digest_triplets(selected))

    def test_scoring_is_aggregate_only_and_read_only(self):
        groups, cat = mtt.triplets_by_vote(self.comparisons, self.clips)
        chosen = mtt.dev_selection(groups, cat, count=4, seed=20261021)
        before = self.db.read_bytes()
        data = mtt.evaluate(self.db, chosen, groups)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(set(data), {"genre", "moodtheme"})
        self.assertEqual(set(data["genre"]["metrics"]), set(mtt.ev.METRICS))
        for h in data:
            for metric in data[h]["metrics"].values():
                self.assertEqual(
                    metric["evaluated_questions"]+metric["abstained_questions"],4
                )
        text = json.dumps(data)
        self.assertNotIn("Artist 1", text)
        self.assertNotIn("1.mp3", text)


if __name__ == "__main__":
    unittest.main()
