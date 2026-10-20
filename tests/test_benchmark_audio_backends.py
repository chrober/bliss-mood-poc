"""No binaries/models required: guard the A/B native benchmark against bias."""
import sqlite3
from contextlib import closing
import struct
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_audio_backends as bench


class AudioBackendBenchmarkTests(unittest.TestCase):
    def test_root_mapping_accepts_relative_file_keys_on_windows(self):
        bench.validate_source_roots(Path(r"\\nas\music"), None)
        bench.validate_source_roots(None, None)
        bench.validate_source_roots(Path(r"\\nas\music"), r"Z:\legacy")
        with self.assertRaisesRegex(ValueError, "--library-root requires"):
            bench.validate_source_roots(None, r"Z:\legacy")

    def test_plan_is_paired_and_alternates_backend_order(self):
        plan = bench.experiment_plan([1, 2, 4, 6], repeats=2, seed=22)
        self.assertEqual(len(plan), 16)
        for round_index in (1, 2):
            for count in (1, 2, 4, 6):
                pair = [row[2] for row in plan
                        if row[0] == round_index and row[1] == count]
                self.assertEqual(pair, ["rust", "essentia"] if round_index == 1
                                 else ["essentia", "rust"])

    def test_score_comparison_independent_of_model_fingerprint(self):
        baseline = {("track.flac", "moodtheme"): (3, (0.1, 0.5, 0.8))}
        native = {("track.flac", "moodtheme"): (3, (0.1001, 0.5, 0.8))}
        stats = bench.compare_feature_tables(baseline, native)
        self.assertEqual(stats["patch_count_mismatches"], 0)
        self.assertEqual(stats["compared_scores"], 3)
        self.assertLess(stats["maximum_absolute_score_difference"], 1e-3)

    def test_comparison_detects_missing_class_and_patch_count_drift(self):
        ref = {("track", "genre"): (3, (0.1, 0.2))}
        with self.assertRaises(AssertionError):
            bench.compare_feature_tables(ref, {})
        with self.assertRaises(AssertionError):
            bench.compare_feature_tables(ref, {("track", "genre"): (3, (0.2,))})
        result = bench.compare_feature_tables(ref, {("track", "genre"): (4, (0.1, 0.2))})
        self.assertEqual(result["patch_count_mismatches"], 1)

    def test_fingerprints_must_be_distinct_between_backends(self):
        with tempfile.TemporaryDirectory() as tmp:
            rust_db = Path(tmp) / "rust.db"
            cpp_db = Path(tmp) / "essentia.db"

            def create(path, keys):
                with closing(sqlite3.connect(path)) as conn:
                    conn.execute("PRAGMA user_version=3")
                    conn.execute(
                        "CREATE TABLE feature_tracks "
                        "(track_file TEXT, model_id TEXT, model_key TEXT)"
                    )
                    conn.executemany(
                        "INSERT INTO feature_tracks VALUES (?,?,?)",
                        [(f"track-{n}.flac", head, key)
                         for head, key in keys
                         for n in range(2)]
                    )

            create(rust_db, [("genre", "rust-genre"),
                             ("moodtheme", "rust-mood")])
            create(cpp_db, [("genre", "cpp-genre"),
                            ("moodtheme", "cpp-mood")])
            self.assertEqual(
                bench.verify_backend_fingerprint_separation(rust_db, cpp_db),
                ["genre", "moodtheme"],
            )
            with closing(sqlite3.connect(cpp_db)) as conn:
                conn.execute(
                    "UPDATE feature_tracks SET model_key='rust-genre' "
                    "WHERE model_id='genre'"
                )
            with self.assertRaisesRegex(AssertionError, "must not share"):
                bench.verify_backend_fingerprint_separation(rust_db, cpp_db)
            with closing(sqlite3.connect(cpp_db)) as conn:
                conn.execute(
                    "UPDATE feature_tracks SET model_key='extra-model' "
                    "WHERE track_file='track-0.flac' AND model_id='genre'"
                )
            with self.assertRaisesRegex(AssertionError, "Mixed model fingerprints"):
                bench.model_fingerprints_by_head(cpp_db)

    def test_fail_closed_on_incomplete_result(self):
        bench.validate_report({"analyzed": 5, "pending": 5,
                               "failures": 0, "missing_files": 0}, 5)
        with self.assertRaises(AssertionError):
            bench.validate_report({"analyzed": 4, "pending": 5,
                                   "failures": 1, "missing_files": 0}, 5)

    def test_readonly_bliss_cohort_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cohort.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.executescript("CREATE TABLE TracksV2 (File TEXT, Ignore INTEGER);")
                conn.executemany("INSERT INTO TracksV2 VALUES (?, 0)",
                                 ((f"song-{i}.flac",) for i in range(3)))
            self.assertEqual(len(bench.checked_cohort(db)), 3)
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("DELETE FROM TracksV2 WHERE File <> 'song-0.flac'")
            with self.assertRaises(ValueError):
                bench.checked_cohort(db)

    def test_load_little_endian_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "features.db"
            with closing(sqlite3.connect(db)) as conn:
                conn.executescript(
                    "CREATE TABLE feature_tracks (track_file TEXT, model_id TEXT, "
                    "patches_analyzed INTEGER, scores_f32_le BLOB);"
                )
                conn.execute(
                    "INSERT INTO feature_tracks VALUES (?,?,?,?)",
                    ("song.mp3", "voice", 3, struct.pack("<ff", 0.25, 0.75)),
                )
            rows = bench.load_feature_rows(db)
            self.assertEqual(rows["song.mp3", "voice"], (3, (0.25, 0.75)))


if __name__ == "__main__":
    unittest.main()
