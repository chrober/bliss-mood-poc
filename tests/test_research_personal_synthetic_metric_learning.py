"""WP2-P3 purely fictional grouped Personal Metric Learning regression gates."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_personal_synthetic_metric_learning as p
from research_grouped_split import grouped_triplet_partition
from research_personal_triplet_protocol import distance, frozen_matrix


class FictionalPersonalLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = p.run()

    def test_grouped_training_and_holdout_strictly_separate(self):
        for scenario in ("axis_sparse", "cross_feature"):
            triplets, features, metadata = p.fictional_cohort(p.SEED, scenario)
            part = grouped_triplet_partition(
                triplets, metadata, seed=p.SEED, test_fraction=0.25)
            self.assertEqual(len(triplets), 48*8)
            self.assertEqual(len(features), 48*6)
            self.assertEqual(part["group_component_count"], 48)
            train = {k for i in part["train_triplet_indices"] for k in triplets[i]}
            holdout = {k for i in part["holdout_triplet_indices"]
                       for k in triplets[i]}
            self.assertFalse(train & holdout)
            for field in ("artist_group", "album_group", "recording_group"):
                self.assertFalse({metadata[k][field] for k in train} &
                                 {metadata[k][field] for k in holdout})
            self.assertTrue(len(part["train_triplet_indices"]) >= 100)
            self.assertTrue(len(part["holdout_triplet_indices"]) >= 1)

    def test_frozen_learning_curve_and_cold_start(self):
        report = self.report
        self.assertEqual(report["status"],
              "SYNTHETIC_ONLY_NO_MEASURED_MUSICAL_PERSONAL_IMPROVEMENT")
        self.assertFalse(report["real_human_votes_or_audio_used"])
        self.assertFalse(report["personal_model_validated_or_deployed"])
        self.assertFalse(report["private_song_id_feature_or_weight_exported"])
        self.assertFalse(report["general_metric_selected"])
        for scenario in report["scenarios"].values():
            self.assertEqual(scenario["learning_curve_train_question_counts"],
                             [0, 10, 25, 50, 100])
            self.assertEqual(scenario["connected_identity_groups"], 48)
            self.assertTrue(scenario[
                "train_holdout_artist_album_recording_and_triplet_disjoint"])
            baseline = scenario["frozen_train_only_learning_curve"]["0"][
                "raw_bliss23_euclidean"]
            for checkpoint in ("0", "10", "25", "50", "100"):
                methods = scenario["frozen_train_only_learning_curve"][checkpoint]
                self.assertEqual(set(methods), {
                    "raw_bliss23_euclidean", "diagonal", "diagonal_plus_rank2"})
                self.assertEqual(methods["raw_bliss23_euclidean"], baseline)
                for stats in methods.values():
                    self.assertEqual(stats["denominator"],
                                     scenario["holdout_question_count"])
                    self.assertEqual(
                        stats["accuracy_with_ambiguous_as_incorrect"],
                        stats["correct"] / stats["denominator"])
                    self.assertTrue(0 <= stats["correct"] <= stats["denominator"])
            self.assertEqual(
                scenario["frozen_train_only_learning_curve"]["0"]["diagonal"],
                baseline)
            self.assertEqual(
                scenario["frozen_train_only_learning_curve"]["0"]["diagonal_plus_rank2"],
                baseline)

    def test_holdout_labels_do_not_touch_fitted_model(self):
        triplets, features, metadata = p.fictional_cohort(p.SEED, "axis_sparse")
        part = grouped_triplet_partition(
            triplets, metadata, seed=p.SEED, test_fraction=0.25)
        train = part["train_triplet_indices"][:25]
        altered = list(triplets)
        for idx in part["holdout_triplet_indices"]:
            a, b, odd = altered[idx]
            altered[idx] = (a, odd, b)
        for capacity in p.CAPACITIES:
            original = p.fit(triplets, features, train, capacity=capacity, seed=7)
            changed = p.fit(tuple(altered), features, train,
                            capacity=capacity, seed=7)
            self.assertEqual(original, changed)

    def test_legacy_matrix_shape_and_numerical_mahalanobis_parity(self):
        triple, features, _ = p.fictional_cohort(10, "cross_feature")
        indices = tuple(range(10))
        for capacity in p.CAPACITIES:
            matrix = p.fit(triple, features, indices,
                           capacity=capacity, seed=11)
            self.assertEqual(len(matrix.diagonal), 23)
            self.assertTrue(all(w > 0 for w in matrix.diagonal))
            if capacity == "diagonal_plus_rank2":
                self.assertEqual(len(matrix.factors), 2)
            legacy = p.matrix_as_legacy(matrix)
            checked = frozen_matrix(legacy)
            a, b, _ = triple[0]
            d=math.sqrt(p.squared_distance(features[a], features[b], matrix))
            self.assertAlmostEqual(d, distance(features[a], features[b], checked),
                                   places=7)

    def test_bad_training_labels_dimensions_and_nonfinite_values(self):
        triple, features, _ = p.fictional_cohort(10, "axis_sparse")
        for invalid in ("full_unrestricted", "legacy_rust_learner"):
            with self.assertRaises(ValueError):
                p.fit(triple, features, [0], capacity=invalid, seed=7)
        for indices in ((-1,), (0, 0), (len(triple),)):
            with self.assertRaises(ValueError):
                p.fit(triple, features, indices, capacity="diagonal", seed=7)
        with self.assertRaises(ValueError):
            p.squared_distance((0.0,), (1.0,), p.Model((1.,)*23))
        with self.assertRaises(ValueError):
            p.squared_distance((float("nan"),)+(0.,)*22,
                               (0.,)*23, p.Model((1.,)*23))
        with self.assertRaises(ValueError):
            p.squared_distance((0.,)*23, (0.,)*23, p.Model((-1.,)*23))

    def test_synthetic_general_personal_blend_and_fallback(self):
        gate = self.report["blend_contract_simulation"]
        self.assertFalse(gate["independent_real_score_calibration_demonstrated"])
        self.assertFalse(gate["production_model_eligible_for_activation"])
        self.assertTrue(gate["assumed_prevalidated_personal_model_is_fictional"])
        self.assertEqual(set(gate["five_settings_tested"]),
                         {"0", "25", "50", "75", "100"})
        for percent, status in gate["five_settings_tested"].items():
            self.assertEqual(status["simulation_valid_model_effective_percent"],
                             int(percent))
            self.assertEqual(
                status["missing_or_uncertified_model_effective_percent"], 0)
            self.assertTrue(status["full_query_fallback_verified"])

    def test_sanitized_and_reproducible_no_song_export(self):
        raw = json.dumps(self.report, sort_keys=True)
        self.assertNotIn("fictional-artist-", raw)
        self.assertNotIn("fictional-recording-", raw)
        self.assertNotIn("model_weights", raw)
        self.assertNotIn("embedding_1280", raw)
        a, f, m = p.fictional_cohort(7, "axis_sparse")
        b, g, n = p.fictional_cohort(7, "axis_sparse")
        self.assertEqual((a,f,m), (b,g,n))


if __name__ == "__main__":
    unittest.main()
