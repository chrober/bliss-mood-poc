import csv
from contextlib import closing
import importlib.util
import json
import math
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_similarity.py"
spec = importlib.util.spec_from_file_location("evaluate_similarity", SCRIPT)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


class SimilarityMathTests(unittest.TestCase):
    def test_identical_and_opposite_activation_patterns(self):
        a = (0.9, 0.1, 0.8, 0.2)
        b = (0.9, 0.1, 0.8, 0.2)
        c = (0.1, 0.9, 0.2, 0.8)
        for name, fn in ev.METRIC_FUNCS.items():
            with self.subTest(metric=name):
                self.assertAlmostEqual(fn(a, b), 1.0, places=6)
                self.assertLess(fn(a, c), fn(a, b))
        self.assertAlmostEqual(ev.centered_cosine(a, c), -1, places=6)

    def test_topk_is_explicitly_sparse(self):
        a = (0.01, 0.03, 0.6, 0.8)
        b = (0.02, 0.04, 0.7, 0.9)
        c = (0.01, 0.03, 0.01, 0.02)
        self.assertGreater(ev.topk_weighted_jaccard(a, b), 0.7)
        self.assertEqual(ev.topk_weighted_jaccard(a, c), 0)
        self.assertIsNone(ev.topk_weighted_jaccard(c, c))

    def test_vectors_must_have_valid_dimensions_and_values(self):
        self.assertIsNone(ev.decode_blob(b"abc", 2))
        self.assertIsNone(ev.decode_blob(struct.pack("<2f", float("nan"), 0.3), 2))
        self.assertIsNone(ev.decode_blob(struct.pack("<2f", 1.2, 0.3), 2))
        self.assertIsNone(ev.decode_blob(struct.pack("<2f", 0.2, 0.2), 2))
        self.assertIsNotNone(ev.decode_blob(struct.pack("<2f", 0.2, 0.8), 2))
        self.assertIsNone(ev.cosine((0, 0), (0, 0)))
        self.assertIsNone(ev.rms((0.1, 0.4), (0.3,)))
        self.assertEqual(ev.describe([]), {"count": 0})

    def test_auc_is_tie_aware_and_requires_two_classes(self):
        self.assertEqual(ev.auc([.9, .6], [.2, .4]), 1.0)
        self.assertEqual(ev.auc([.2], [.2]), .5)
        self.assertEqual(ev.auc([.1], []), None)


class ReadOnlySimilarityEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbfile = Path(self.tmp.name) / "features.db"
        conn = sqlite3.connect(self.dbfile)
        conn.executescript("""
            PRAGMA user_version=3;
            CREATE TABLE feature_models(
                model_key TEXT PRIMARY KEY,
                preprocessing_version TEXT NOT NULL,
                aggregation TEXT NOT NULL,
                classes_json TEXT NOT NULL,
                validated_against_essentia INTEGER NOT NULL
            );
            CREATE TABLE feature_tracks(
                track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                capability TEXT NOT NULL, model_key TEXT NOT NULL,
                scores_f32_le BLOB NOT NULL,
                PRIMARY KEY(track_file,model_id)
            );
        """)
        for model, (capability, dimensions) in ev.MODELS.items():
            labels = [f"{model}-{i}" for i in range(dimensions)]
            conn.execute(
                "INSERT INTO feature_models VALUES(?,?,?,?,0)",
                (f"{model}-new", "v1", ev.AGGREGATION, json.dumps(labels)),
            )
            # Old fingerprint must NEVER mix with the new cohort.
            conn.execute(
                "INSERT INTO feature_models VALUES(?,?,?,?,1)",
                (f"{model}-old", "v1", ev.AGGREGATION, json.dumps(labels)),
            )
            for index, file in enumerate([
                "Rock/A.flac", "Rock/B.flac",
                "Metal/C.flac", "Metal/D.flac",
            ]):
                vec = [0.8 if (i % 2 == (0 if index < 2 else 1)) else 0.1
                       for i in range(dimensions)]
                if index in (1, 3):
                    vec[0] += .01
                conn.execute(
                    "INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                    (file, model, capability, f"{model}-new",
                     struct.pack("<" + "f" * dimensions, *vec)),
                )
            conn.execute(
                "INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                ("Old/Unrelated.flac", model, capability, f"{model}-old",
                 struct.pack("<" + "f" * dimensions,
                             *[0.6 if i % 2 else .1 for i in range(dimensions)])),
            )
        conn.commit()
        conn.close()

    def test_default_requires_validated_and_does_not_write(self):
        initial = self.dbfile.read_bytes()
        with self.assertRaisesRegex(ValueError, "include-experimental"):
            ev.report(self.dbfile, 4, 10, 12, 2, False, None)
        output = ev.report(self.dbfile, 4, 10, 12, 2, True, None)
        self.assertEqual(output["mode"], "experimental")
        self.assertEqual(output["sampling"]["paired_valid_total"], 4)
        self.assertEqual(output["sampling"]["sample_size"], 4)
        self.assertTrue(output["source"]["read_only"])
        self.assertEqual(initial, self.dbfile.read_bytes())
        self.assertEqual(output["models"]["genre"]["model_key"], "genre-new")
        self.assertEqual(output["models"]["moodtheme"]["model_key"], "moodtheme-new")
        self.assertEqual(output, ev.report(self.dbfile, 4, 10, 12, 2, True, None))

    def test_explicit_labels_discriminate_examples(self):
        labels = Path(self.tmp.name) / "judged.csv"
        with labels.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(("left", "right", "label"))
            writer.writerow(("Rock/A.flac", "Rock/B.flac", "1"))
            writer.writerow(("Metal/C.flac", "Metal/D.flac", "1"))
            writer.writerow(("Rock/A.flac", "Metal/C.flac", "0"))
            writer.writerow(("Rock/B.flac", "Metal/D.flac", "0"))
            writer.writerow(("Rock/A.flac", "Unknown/Not In DB.flac", "0"))
        output = ev.report(self.dbfile, 4, 10, 12, 0, True, labels)
        self.assertEqual(output["labeled"]["judged_pairs"], 5)
        for head in ev.MODELS:
            self.assertEqual(output["labeled"][head]["pairs_missing_compatible_vectors"], 1)
            for metric, result in output["labeled"][head]["metrics"].items():
                with self.subTest(head=head, metric=metric):
                    self.assertEqual(result["roc_auc"], 1)
                    self.assertEqual(result["positives"]["count"], 2)
                    self.assertEqual(result["negatives"]["count"], 2)

    def test_duplicate_labels_rejected(self):
        file = Path(self.tmp.name) / "labels.csv"
        file.write_text(
            "left,right,label\nRock/A.flac,Rock/B.flac,1\n"
            "Rock/B.flac,Rock/A.flac,0\n", encoding="utf8"
        )
        with self.assertRaisesRegex(ValueError, "Duplicate judged pair"):
            ev.load_labels(file)

    def test_missing_db_does_not_create_a_file(self):
        path = Path(self.tmp.name) / "missing.db"
        with self.assertRaises(FileNotFoundError):
            ev.open_database(path)
        self.assertFalse(path.exists())

    def test_rejects_wrong_sqlite_schema(self):
        # sqlite3.Connection's context manager commits/rolls back, but does
        # NOT close the handle. Windows cannot remove our TemporaryDirectory
        # while that connection is still open.
        with closing(sqlite3.connect(self.dbfile)) as conn:
            conn.execute("PRAGMA user_version=2")
        with self.assertRaisesRegex(ValueError, "schema v3"):
            ev.open_database(self.dbfile)


if __name__ == "__main__":
    unittest.main()
