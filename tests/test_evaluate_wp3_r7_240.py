"""Synthetic-only WP3-R7 uncertainty, group and retrieval regression gates."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_wp3_r7_240 as r7
import evaluate_wp3_r6_240 as r6
from research_bliss_essentia_teacher_models import _requires_sklearn


class PostR6ExploratoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.np = _requires_sklearn()[0]

    def test_locked_report_tamper_and_numeric_reproduction(self):
        r7._assert_same({"head": {"rho": 0.4390345718}, "status": True},
                        {"head": {"rho": 0.43903457182}, "status": True})
        with self.assertRaises(ValueError):
            r7._assert_same({"rho": .439}, {"rho": .440})
        with self.assertRaises(ValueError):
            r7._assert_same({"rho": .439}, {"rho": .439, "private": "x"})

    def _manifest(self):
        return {"selected_songs": [
            {"track_file": "private" + str(i),
             "artist_keys": ["artist" + str(i), "collaborator" + str(i)],
             "lms_album_id": i,
             "recording_mbid": "mbid" + str(i)}
            for i in range(240)
        ]}

    def test_group_disjointness_checks_artists_collaborators_albums_recordings(self):
        manifest = self._manifest()
        r7._validate_singleton_groups(manifest)
        for field, value in (
                ("artist_keys", ["collaborator0", "artist1"]),
                ("lms_album_id", 0), ("recording_mbid", "mbid0")):
            changed = self._manifest()
            changed["selected_songs"][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                r7._validate_singleton_groups(changed)

    def test_retrieval_excludes_query_and_respects_stable_ties(self):
        np = self.np
        idx = np.arange(25)
        teacher = np.abs(idx[:, None] - idx[None, :]).astype(float)
        overlap = r7._retrieval(np, teacher, teacher)
        for key in ("top_5_mean_teacher_neighbor_overlap",
                    "top_10_mean_teacher_neighbor_overlap",
                    "top_20_mean_teacher_neighbor_overlap"):
            self.assertEqual(overlap[key], 1.0)
        reversed_teacher = teacher[::-1, ::-1].copy()
        mismatch = r7._retrieval(np, reversed_teacher, teacher)
        self.assertLess(mismatch["top_5_mean_teacher_neighbor_overlap"], 1.0)

    def test_bootstrap_resamples_song_groups_not_28680_pairs(self):
        np = self.np
        rng = np.random.default_rng(12)
        X = rng.normal(size=(25, 4))
        from scipy.spatial.distance import cdist
        matrix = cdist(X, X)
        result = r7._bootstrap_delta(np, matrix, matrix, matrix,
                                     repetitions=50, seed=17)
        self.assertEqual(result["bootstrap_samples"], 50)
        self.assertEqual(result["percentile_95_interval"], [0.0, 0.0])
        self.assertFalse(result["confirmatory_significance_test"])
        with self.assertRaises(ValueError):
            r7._bootstrap_delta(np, matrix, matrix[:24, :24], matrix,
                                repetitions=50)

    def test_eight_representations_plus_two_teacher_distances(self):
        np = self.np
        rng = np.random.default_rng(3)
        old_x = rng.normal(size=(100, 23))
        new_x = rng.normal(size=(240, 23))
        old_mood = rng.normal(size=(100, 56))
        old_genre = rng.normal(size=(100, 87))
        new_mood = rng.normal(size=(240, 56))
        new_genre = rng.normal(size=(240, 87))
        embedding = rng.normal(size=(240, 1280))
        d = r7._distance_matrices(np, new_x, old_x, old_mood, old_genre,
                                  new_mood, new_genre, embedding)
        self.assertEqual(len(d), 10)
        self.assertIn("frozen_genre_pls2_student_euclidean", d)
        for name, matrix in d.items():
            with self.subTest(method=name):
                self.assertEqual(matrix.shape, (240, 240))
                self.assertTrue(np.isfinite(matrix).all())
                self.assertTrue(np.allclose(matrix, matrix.T, atol=1e-10))
                self.assertTrue(np.allclose(np.diag(matrix), 0.0))
        # New-cohort labels are used as teacher references, never as fit targets.
        d2 = r7._distance_matrices(np, new_x, old_x, old_mood, old_genre,
                                   new_mood + 3, new_genre + 1, embedding)
        for name in ("frozen_moodtheme_ridge_student_euclidean",
                     "frozen_genre_pls2_student_euclidean"):
            self.assertTrue(np.array_equal(d[name], d2[name]))


if __name__ == "__main__":
    unittest.main()
