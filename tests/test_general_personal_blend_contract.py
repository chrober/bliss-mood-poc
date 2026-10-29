"""WP2-P0 synthetic personal-model fallback, blending and legacy schema tests."""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import general_personal_blend_contract as b


class PersonalBlendContractTests(unittest.TestCase):
    def setUp(self):
        self.general = (0.1, 0.3, 0.7, 1.0)
        self.personal_scores = (0.9, 0.5, 0.3, 0.0)
        self.model = b.PersonalEvidence(
            profile_id="opaque-test-profile",
            feature_fingerprint="opaque-test-feature-fingerprint",
            score_calibration_id="frozen-calibration-v1",
            candidate_cohort_fingerprint="query-candidate-set-fixed-v1",
            version=1,
            quality_validated=True,
            calibration_validated=True,
            scores=self.personal_scores,
        )
        self.args = dict(
            expected_profile=self.model.profile_id,
            expected_feature_fingerprint=self.model.feature_fingerprint,
            expected_score_calibration_id=self.model.score_calibration_id,
            expected_candidate_cohort_fingerprint=self.model.candidate_cohort_fingerprint,
        )

    def score(self, percent, personal=None, general=None, **overrides):
        return b.choose_scores(
            self.general if general is None else general,
            requested_personal_percent=percent,
            personal=personal,
            **(self.args | overrides),
        )

    def test_five_frozen_influence_points(self):
        for percent in (0, 25, 50, 75, 100):
            outcome = self.score(percent, self.model)
            self.assertEqual(outcome.requested_personal_percent, percent)
            self.assertEqual(outcome.effective_personal_percent, percent)
            self.assertEqual(outcome.fallback_reason,
                             "personal_disabled_by_requested_zero_percent"
                             if percent == 0 else "none")
            expected = tuple(
                (1 - percent/100) * g + percent/100 * p
                for g, p in zip(self.general, self.personal_scores)
            )
            for a, e in zip(outcome.scores, expected):
                self.assertAlmostEqual(a, e, places=14)
        self.assertEqual(self.score(0, self.model).scores, self.general)
        self.assertEqual(self.score(100, self.model).scores, self.personal_scores)

    def test_absent_model_and_unavailable_calibration_fallback_all_candidates(self):
        for p in (1, 25, 50, 100):
            absent = self.score(p)
            self.assertEqual(absent.scores, self.general)
            self.assertEqual(absent.effective_personal_percent, 0)
            self.assertEqual(absent.fallback_reason, "no_personal_model")
            uncalibrated = self.score(
                p, replace(self.model, calibration_validated=False)
            )
            self.assertEqual(uncalibrated.scores, self.general)
            self.assertEqual(uncalibrated.effective_personal_percent, 0)

    def test_wrong_profile_cohort_feature_calibration_or_version_fall_back(self):
        scenarios = [
            replace(self.model, profile_id="other-user"),
            replace(self.model, candidate_cohort_fingerprint="other-query"),
            replace(self.model, feature_fingerprint="wrong-vector-order"),
            replace(self.model, score_calibration_id="wrong-scorer-scale"),
            replace(self.model, version=2),
            replace(self.model, quality_validated=False),
            replace(self.model, scores=(0.1, 0.2)),
            replace(self.model, scores=(0.1, math.nan, 0.3, 0.4)),
            replace(self.model, scores=(0.1, -0.1, 0.3, 0.4)),
            replace(self.model, scores=(0.1, 0.2, 0.3, 1.001)),
        ]
        for model in scenarios:
            with self.subTest(model=model):
                result = self.score(100, model)
                self.assertEqual(result.scores, self.general)
                self.assertEqual(result.effective_personal_percent, 0)
                self.assertNotEqual(result.fallback_reason, "none")

    def test_general_validated_even_at_100_personal(self):
        for invalid in ((), (0.5, float("nan")), (1.00001,), (True,), (None,)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.score(100, self.model, general=invalid)

    def test_bad_percentage_never_silently_clamped(self):
        for bad in (-1, 101, 50.0, True, None, "100"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.score(bad, self.model)

    def test_corrupted_and_legacy_matrix_only_format_not_model_certification(self):
        old = {"m": {"v": 1, "dim": [23, 23], "data": [0.0] * 529}}
        outcome = b.inspect_legacy_bliss_matrix(old)
        self.assertTrue(outcome["structurally_compatible"])
        self.assertFalse(outcome["positive_semidefinite_certified"])
        self.assertFalse(outcome["may_activate_general_personal_blend"])
        for corrupted in (
            {}, {"m": {"v": 2, "dim": [23, 23], "data": [0.]*529}},
            {"m": {"v": 1, "dim": [23, 22], "data": [0.]*529}},
            {"m": {"v": 1, "dim": [23, 23], "data": [0.]*528}},
            {"m": {"v": 1, "dim": [23, 23], "data": [math.inf]*529}},
        ):
            self.assertFalse(b.inspect_legacy_bliss_matrix(corrupted)["structurally_compatible"])

    def test_existing_lab_triplets_no_leak_and_orientation_conserved(self):
        sample = [
            ["Artist/1", "Artist/2", "Artist/3"],
            ["Artist/2", "Artist/1", "Artist/3"], # same similar pair
            ["Artist/1", "Artist/3", "Artist/2"], # different odd label
            ["Artist/1", "Artist/1", "Artist/3"],
            ["Artist/1", "Artist/2"],
        ]
        counts = b.legacy_triplet_counts(sample)
        self.assertEqual(counts["valid_unique_ordered_role_triplets"], 2)
        self.assertEqual(counts["duplicate_triplets"], 1)
        self.assertEqual(counts["invalid_triplets"], 2)
        self.assertNotIn("Artist", str(counts))
        with self.assertRaises(ValueError):
            b.legacy_triplet_counts({})

if __name__ == "__main__":
    unittest.main()
