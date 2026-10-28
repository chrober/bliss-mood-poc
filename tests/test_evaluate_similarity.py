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

    def test_topk_zero_overlap_is_not_falsely_ranked_as_a_neighbor(self):
        # Zero Jaccard means no shared active class. Do not fabricate a
        # "top match" by alphabetically sorting equally bad candidates.
        vectors = {
            "A.flac": (0.9, 0.01, 0.01, 0.01),
            "B.flac": (0.01, 0.9, 0.01, 0.01),
            "C.flac": (0.01, 0.01, 0.9, 0.01),
        }
        sample = {"tracks": {
            key: {"genre": values, "moodtheme": values}
            for key, values in vectors.items()
        }}
        cohorts = {
            key: {"labels": ["first", "second", "third", "fourth"]}
            for key in ev.MODELS
        }
        result = ev.evaluate_random(sample, 10, 3, 3, cohorts)
        for head in ev.MODELS:
            zero_only = [
                item for item in result[head]["nearest_neighbor_examples"]
                if item["metric"] == "topk_weighted_jaccard"
            ]
            self.assertEqual(len(zero_only), 3)
            for item in zero_only:
                self.assertEqual(item["neighbors"], [])
                self.assertTrue(item["no_positive_overlap"])
                self.assertEqual(item["zero_score_candidates"], 2)
                self.assertEqual(item["undefined_score_candidates"], 0)
            stats = result[head]["random_pairs"]["topk_weighted_jaccard"]
            self.assertEqual(stats["zero_fraction"], 1.0)
            profiles = result[head]["track_profiles"]
            self.assertEqual(len(profiles), 3)
            self.assertEqual(profiles[0]["top_classes"][0]["label"], "first")
            self.assertEqual(profiles[0]["active_ge_0_10"], 1)

    def test_profiles_come_from_actual_ordered_model_labels(self):
        profile = ev.feature_profile(
            "song", (0.02, 0.8, 0.9, 0.01),
            ["ambient", "blues", "folk", "rock"],
        )
        self.assertEqual(
            [x["label"] for x in profile["top_classes"][:2]],
            ["folk", "blues"],
        )
        self.assertEqual(profile["active_ge_0_10"], 2)

    def test_low_activation_vectors_rank_without_arbitrary_absolute_cutoff(self):
        # All valid Mood values may be below 0.10, as in the real Aretha
        # Franklin recording. Lack of threshold crossing is not lack of
        # vector evidence: threshold-free top-K still evaluates their ranks.
        a = (0.0815, 0.0738, 0.0640, 0.0601, 0.0498, 0.0473, 0.03)
        b = (0.0780, 0.0690, 0.0620, 0.0590, 0.0520, 0.0430, 0.02)
        self.assertIsNone(ev.topk_weighted_jaccard(a, b))
        self.assertGreater(ev.METRIC_FUNCS["topk6_ranked_jaccard"](a, b), 0)
        self.assertGreater(ev.METRIC_FUNCS["topk12_ranked_jaccard"](a, b), 0)
        # No production calibration, threshold or universal optimal K implied.
        self.assertEqual(ev.METRICS[-2:],
                         ("topk6_ranked_jaccard", "topk12_ranked_jaccard"))

    def test_sparsity_report_is_auditable_per_head(self):
        tracks = {"seed1": (.0815, .0738, .0640, .0601),
                  "seed2": (.35, .25, .05, .01)}
        sample = {"tracks": {
            key: {head: v for head in ev.MODELS}
            for key, v in tracks.items()
        }}
        output = ev.evaluate_random(sample, 8, 1, 0)
        for head in ev.MODELS:
            activation = output[head]["activation_distribution"]
            self.assertEqual(activation["tracks_no_classes_ge_0_10"], 1)
            self.assertEqual(activation["active_classes_ge_0_10"]["median"], 1)
            self.assertEqual(activation["maximum"]["count"], 2)
            self.assertEqual(
                output[head]["random_pairs"]["topk6_ranked_jaccard"]["count"], 8
            )

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

    def test_independent_genre_and_mood_labels_do_not_leak(self):
        labels = Path(self.tmp.name) / "judged.csv"
        with labels.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(("left", "right", "genre_label", "mood_label"))
            # Synthetic feature vectors are intentionally paired by group.
            # The mocked human genre judgments agree with that structure;
            # the mood judgments explicitly DISAGREE to prove separation.
            writer.writerow(("Rock/A.flac", "Rock/B.flac", "1", "0"))
            writer.writerow(("Metal/C.flac", "Metal/D.flac", "1", "0"))
            writer.writerow(("Rock/A.flac", "Metal/C.flac", "0", "1"))
            writer.writerow(("Rock/B.flac", "Metal/D.flac", "0", "1"))
            writer.writerow(("Rock/A.flac", "Unknown/Not In DB.flac", "0", ""))
            writer.writerow(("Rock/A.flac", "Metal/D.flac", "", "1"))
        output = ev.report(self.dbfile, 4, 10, 12, 0, True, labels)
        self.assertEqual(output["labeled"]["judged_pairs"], 6)
        self.assertEqual(output["labeled"]["genre"]["pairs_judged_for_head"], 5)
        self.assertEqual(output["labeled"]["moodtheme"]["pairs_judged_for_head"], 5)
        self.assertEqual(output["labeled"]["genre"]["pairs_missing_compatible_vectors"], 1)
        self.assertEqual(output["labeled"]["moodtheme"]["pairs_missing_compatible_vectors"], 0)
        for metric in ev.METRICS:
            with self.subTest(metric=metric):
                genre = output["labeled"]["genre"]["metrics"][metric]
                mood = output["labeled"]["moodtheme"]["metrics"][metric]
                self.assertEqual(genre["roc_auc"], 1)
                self.assertEqual(mood["roc_auc"], 0)
                self.assertEqual(genre["positives"]["count"], 2)
                self.assertEqual(genre["negatives"]["count"], 2)
                self.assertEqual(mood["positives"]["count"], 3)
                self.assertEqual(mood["negatives"]["count"], 2)

    def test_semicolon_csv_and_exact_pair_diagnostics_are_read_only(self):
        labels = Path(self.tmp.name) / "judged-semicolon.csv"
        with labels.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(("left", "right", "genre_label", "mood_label"))
            writer.writerow(("Rock/A.flac", "Rock/B.flac", "1", "0"))
            writer.writerow(("Rock/A.flac", "Metal/C.flac", "0", "1"))
            writer.writerow(("Rock/B.flac", "Metal/D.flac", "0", "1"))

        before_db = self.dbfile.read_bytes()
        before_labels = labels.read_bytes()
        report = ev.pair_details_report(self.dbfile, True, labels)

        self.assertEqual(report["schema"], "similarity-pair-diagnostics-v1")
        self.assertTrue(report["source"]["read_only"])
        self.assertEqual(report["labeled"]["judged_pairs"], 3)
        self.assertEqual(len(report["pair_details"]), 3)
        self.assertEqual(
            [(pair["genre_label"], pair["mood_label"])
             for pair in report["pair_details"]],
            [(1, 0), (0, 1), (0, 1)],
        )
        self.assertEqual(
            report["models"]["moodtheme"]["model_key"], "moodtheme-new"
        )
        for pair in report["pair_details"]:
            self.assertEqual(set(pair["scores"]), set(ev.MODELS))
            for head in ev.MODELS:
                self.assertEqual(set(pair["scores"][head]), set(ev.METRICS))
        for head in ev.MODELS:
            for metric in ev.METRICS:
                scores = report["pair_details"]
                positives = [p["scores"][head][metric] for p in scores
                             if p["genre_label" if head == "genre" else "mood_label"] == 1]
                negatives = [p["scores"][head][metric] for p in scores
                             if p["genre_label" if head == "genre" else "mood_label"] == 0]
                self.assertEqual(
                    ev.auc([v for v in positives if v is not None],
                           [v for v in negatives if v is not None]),
                    report["labeled"][head]["metrics"][metric]["roc_auc"],
                )
        self.assertEqual(self.dbfile.read_bytes(), before_db)
        self.assertEqual(labels.read_bytes(), before_labels)

    def test_pair_diagnostics_do_not_require_or_perform_random_sampling(self):
        labels = Path(self.tmp.name) / "single.csv"
        labels.write_text(
            "left;right;genre_label;mood_label\n"
            "Rock/A.flac;Metal/C.flac;0;1\n", encoding="utf-8"
        )
        output = ev.pair_details_report(self.dbfile, True, labels)
        self.assertEqual(len(output["pair_details"]), 1)
        self.assertNotIn("unlabeled", output)
        self.assertEqual(output["labeled"]["moodtheme"]["pairs_judged_for_head"], 1)
        self.assertIsNone(output["labeled"]["moodtheme"]["metrics"]["cosine"]["roc_auc"])

    def test_duplicate_labels_rejected(self):
        file = Path(self.tmp.name) / "labels.csv"
        file.write_text(
            "left,right,genre_label,mood_label\n"
            "Rock/A.flac,Rock/B.flac,1,\n"
            "Rock/B.flac,Rock/A.flac,,0\n", encoding="utf8"
        )
        with self.assertRaisesRegex(ValueError, "Duplicate judged pair"):
            ev.load_labels(file)

    def test_shared_labels_rejected_and_blank_is_allowed_per_head(self):
        file = Path(self.tmp.name) / "labels.csv"
        file.write_text("left,right,label\nRock/A.flac,Rock/B.flac,1\n",
                        encoding="utf8")
        with self.assertRaisesRegex(ValueError, "genre_label,mood_label"):
            ev.load_labels(file)
        file.write_text(
            "left,right,genre_label,mood_label\n"
            "Rock/A.flac,Rock/B.flac,,1\n", encoding="utf8"
        )
        parsed = ev.load_labels(file)
        self.assertEqual(parsed[0][2], {"genre": None, "moodtheme": 1})
        file.write_text(
            "left,right,genre_label,mood_label\n"
            "Rock/A.flac,Rock/B.flac,,\n", encoding="utf8"
        )
        with self.assertRaisesRegex(ValueError, "at least one head label"):
            ev.load_labels(file)
        file.write_text(
            "left,right,genre_label,mood_label\n"
            "Rock/A.flac,Rock/B.flac,2,0\n", encoding="utf8"
        )
        with self.assertRaisesRegex(ValueError, "genre_label must"):
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
