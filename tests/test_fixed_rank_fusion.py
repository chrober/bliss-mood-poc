"""Offline tests for preregistered, triplet-local, equal-weight fusion only."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fixed_rank_fusion import FIXED_FUSIONS, predict, scores_to_local_ranks


class RankFusionTests(unittest.TestCase):
    def test_predeclared_combinations_are_fixed_and_unweighted(self):
        self.assertEqual(list(FIXED_FUSIONS), [
            "rank_audio_genre_equal", "rank_audio_mood_equal",
            "rank_genre_mood_equal", "rank_audio_genre_mood_equal",
        ])
        self.assertEqual(FIXED_FUSIONS["rank_audio_genre_mood_equal"],
                         ("embedding", "genre", "moodtheme"))

    def test_midranks_and_ties(self):
        self.assertEqual(scores_to_local_ranks([.1,.8,.3]), (0.,1.,.5))
        self.assertEqual(scores_to_local_ranks([.1,.1,.9]), (.25,.25,1.))
        self.assertEqual(scores_to_local_ranks([.7,.7,.7]), (.5,.5,.5))
        with self.assertRaises(ValueError):
            scores_to_local_ranks([.1,.2])
        with self.assertRaises(ValueError):
            scores_to_local_ranks([.1,float("nan"),.4])

    def test_equal_models_and_invariance_to_positive_score_scaling(self):
        # a/b strongly aligned (odd-one-out c), genre + audio equal.
        vectors={
            "a": {"embedding": (1.,0.), "genre": (1.,0.), "moodtheme": (1.,0.)},
            "b": {"embedding": (.9,.1), "genre": (.8,.2), "moodtheme": (.99,.01)},
            "c": {"embedding": (-1.,0.), "genre": (-1.,0.), "moodtheme": (-1.,0.)},
        }
        for combo in FIXED_FUSIONS.values():
            self.assertEqual(predict(("a","b","c"), vectors, combo), ("c",None))
        # Positive scaling of vectors preserves cosine and therefore fusion ranks.
        scaled={
            track: {head: tuple(123. * v for v in vector) for head,vector in record.items()}
            for track,record in vectors.items()
        }
        for combo in FIXED_FUSIONS.values():
            self.assertEqual(predict(("a","b","c"), scaled, combo),
                             predict(("a","b","c"), vectors, combo))

    def test_unresolved_and_zero_norm(self):
        vectors={key: {head: (1.,0.) for head in ("embedding","genre","moodtheme")}
                 for key in ("a","b","c")}
        self.assertEqual(predict(("a","b","c"), vectors,
                                 FIXED_FUSIONS["rank_audio_genre_equal"]),
                         (None,"tie"))
        vectors["a"]["embedding"]=(0.,0.)
        self.assertEqual(predict(("a","b","c"), vectors,
                                 FIXED_FUSIONS["rank_audio_genre_equal"]),
                         (None,"undefined"))
        with self.assertRaises(ValueError):
            predict(("a","a","b"), vectors, ("embedding","genre"))
        with self.assertRaises(ValueError):
            predict(("a","b","c"), vectors, ("embedding","genre","extra"))


if __name__ == "__main__":
    unittest.main()
