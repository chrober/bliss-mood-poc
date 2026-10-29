"""Synthetic contracts for label-free, fixed global pairwise Genre/Mood/Audio fusions."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import global_pairwise_fusion as f


class GlobalPairwiseTests(unittest.TestCase):
    def setUp(self):
        self.a = {
            "genre": (0.2, 0.6, 0.1, 0.9),
            "moodtheme": (0.8, 0.1, 0.2, 0.4),
            "embedding": (0.6, 0.8, 0., 0.),
        }
        self.b = {
            "genre": (0.7, 0.2, 0.4, 0.5),
            "moodtheme": (0.4, 0.8, 0.1, 0.3),
            "embedding": (0., 0.8, 0.6, 0.),
        }
        self.c = {
            "genre": (0.8, 0.4, 0.3, 0.1),
            "moodtheme": (0.2, 0.1, 0.9, 0.4),
            "embedding": (0., 0., 0.8, 0.6),
        }

    def test_all_methods_symmetric_and_bounded(self):
        self.assertEqual(len(f.FUSIONS), 4)
        for method in f.FUSIONS:
            with self.subTest(method=method):
                ab = f.pair_score(self.a, self.b, method)
                ba = f.pair_score(self.b, self.a, method)
                self.assertIsNotNone(ab)
                self.assertGreaterEqual(ab, 0)
                self.assertLessEqual(ab, 1)
                self.assertAlmostEqual(ab, ba, places=14)

    def test_candidate_invariance_and_repeated_calls(self):
        """Presence or ordering of unrelated C must not affect S(A,B)."""
        for method in f.FUSIONS:
            s = f.pair_score(self.a, self.b, method)
            for extra in (self.c, self.a, self.b):
                f.pair_score(self.a, extra, method)
                f.pair_score(extra, self.b, method)
                self.assertEqual(s, f.pair_score(self.a, self.b, method))

    def test_expected_affine_score_and_equal_weights(self):
        from evaluate_similarity import centered_cosine, cosine
        genre = (1 + centered_cosine(self.a["genre"], self.b["genre"])) / 2
        mood = (1 + centered_cosine(self.a["moodtheme"], self.b["moodtheme"])) / 2
        audio = (1 + cosine(self.a["embedding"], self.b["embedding"])) / 2
        self.assertAlmostEqual(
            f.pair_score(self.a, self.b, "global_genre_mood_audio_equal"),
            math.fsum((genre, mood, audio)) / 3,
        )
        self.assertAlmostEqual(
            f.pair_score(self.a, self.b, "global_mood_audio_equal"),
            (mood + audio)/2,
        )

    def test_bad_inputs_abstain_not_renormalize(self):
        for method in f.FUSIONS:
            component = f.FUSIONS[method][0]
            head = f.COMPONENTS[component][0]
            missing = dict(self.a)
            del missing[head]
            self.assertIsNone(f.pair_score(missing, self.b, method))
            bad = dict(self.a)
            bad[head] = tuple(float("nan") for _ in self.a[head])
            self.assertIsNone(f.pair_score(bad, self.b, method))
            degenerate = dict(self.a)
            degenerate[head] = tuple(0.0 for _ in self.a[head])
            self.assertIsNone(f.pair_score(degenerate, self.b, method))

    def test_missing_invalid_bool_mismatched_nonfinite(self):
        for bad_vector in ((True, 0.1, 0.4, 0.2), (math.inf, 0., 0., 1.),
                           (0.2,), (0., 0., 0., 0.)):
            d = dict(self.a, genre=bad_vector)
            self.assertIsNone(f.pair_score(d, self.b, "global_genre_audio_equal"))
        with self.assertRaises(ValueError):
            f.pair_score(self.a, self.b, "invented_method")

    def test_spec_is_explicitly_no_training_and_global(self):
        p = f.provenance()
        self.assertFalse(p["label_fitted_weights"])
        self.assertFalse(p["candidate_set_dependent"])
        self.assertFalse(p["preference_training"])
        self.assertEqual(set(p["fusions"]), set(f.FUSIONS))
        self.assertEqual(p["range"], [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
