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

    def test_stratified_sampling_freezes_both_deam_cohorts(self):
        ids = [str(i) for i in range(1, 101)]
        ids += [str(i) for i in range(2001, 2016)]
        labels = {ident: (5.0, 5.0) for ident in ids}
        members = {ident: ident + ".mp3" for ident in ids}

        sample = bench.select_ids(labels, members, 30, 20261021,
                                  stratify_cohorts=True)
        self.assertEqual(sample, bench.select_ids(
            labels, members, 30, 20261021, stratify_cohorts=True))
        self.assertEqual(len(sample), 30)
        self.assertEqual(len(set(sample)), 30)
        self.assertEqual(sum(bench.annotation_cohort(i) == "full_song_2015"
                             for i in sample), 6)
        self.assertEqual(sum(bench.annotation_cohort(i) == "earlier_excerpt"
                             for i in sample), 24)
        with self.assertRaisesRegex(ValueError, "at least 12"):
            bench.select_ids(labels, members, 11, 1, stratify_cohorts=True)

    def test_subcohort_reports_are_separate_and_aggregate_only(self):
        with closing(sqlite3.connect(self.db)) as connection:
            for head, (capability, count) in bench.ev.MODELS.items():
                for i in range(2001, 2007):
                    vec = [0.006 + k * 0.00001 for k in range(count)]
                    vec[0] = .1 + (i - 2000) * .09
                    vec[1] = .9 - (i - 2000) * .09
                    connection.execute(
                        "INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                        (f"DEAM/{i}.mp3", head, capability, f"deam-{head}",
                         struct.pack("<" + "f" * count, *vec)),
                    )
            connection.commit()
        human = bench.load_annotations(self.annotation_zip)
        human.update({str(i): (1.5 + (i - 2000) * .6, 2 + (i - 2000) * .5)
                      for i in range(2001, 2007)})
        ids = [str(i) for i in range(1, 7)] + [str(i) for i in range(2001, 2007)]
        data = bench.evaluate(self.db, ids, human, 123,
                              report_subcohorts=True)
        self.assertEqual(data["dataset"]["annotation_cohort_counts"],
                         {"earlier_excerpt": 6, "full_song_2015": 6})
        self.assertEqual(data["dataset"]["train_overlap_check"], "not_performed")
        self.assertEqual(len(data["dataset"]["sample_id_sha256"]), 64)
        self.assertEqual(set(data["subcohorts"]),
                         {"earlier_excerpt", "full_song_2015"})
        for cohort in data["subcohorts"].values():
            self.assertEqual(cohort["songs_evaluated"], 6)
            self.assertIn("moodtheme", cohort["per_head"])
        self.assertNotIn("DEAM/2001.mp3", json.dumps(data))

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
