"""WP3-R1 synthetic teacher correlations with train-only selection and grouped holdout."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_feature_relationships as r


def cohort(artists=12, per_artist=4):
    rows = []
    for artist in range(artists):
        for item in range(per_artist):
            n = artist*per_artist+item
            x = (n+1)/(artists*per_artist+2)
            # Teacher predicts a synthetic property that was explicitly
            # constructed from Tempo. This is NOT real musical ground truth.
            rows.append({
                "track_id": f"hidden-library/artist-{artist}/track-{item}.mp3",
                "artist_group": f"artist-{artist}",
                "album_group": f"album-{artist}",
                "recording_group": f"recording-{artist}-{item}",
                "bliss": [x] + [0.25]*22,
                "genre": [x] + [0.4]*86,
                "moodtheme": [1.0-x] + [0.3]*55,
            })
    return rows


class CorrelationTests(unittest.TestCase):
    def test_perfect_synthetic_teacher_relationship_recovers_train_and_holdout(self):
        rows = cohort()
        out = r.relationship_report(rows, seed=20261029, test_fraction=0.25, top_k=3)
        self.assertEqual(out["train_song_count"] + out["holdout_song_count"], 48)
        self.assertTrue(out["guarantees"]["artist_album_recording_group_disjoint"])
        self.assertFalse(out["relations"]["genre"]["multiple_comparisons_adjusted"])
        for head, expected in (("genre", 1.0), ("moodtheme", -1.0)):
            summary = out["relations"][head]
            self.assertEqual(summary["possible_feature_teacher_pairs"],
                             23 * (87 if head=="genre" else 56))
            self.assertEqual(summary["estimable_train_spearman_pairs"], 1)
            best = summary["strongest_training_selected_pairs"][0]
            self.assertEqual(best["bliss_feature"], "Tempo")
            self.assertEqual(best["teacher_class_index"], 0)
            self.assertAlmostEqual(best["train_spearman"], expected)
            self.assertAlmostEqual(best["holdout_spearman"], expected)
        rendered = json.dumps(out)
        for private in ("hidden-library", "artist-1", "track-1.mp3", "recording-"):
            self.assertNotIn(private, rendered)

    def test_truly_constant_teacher_dimensions_are_not_spurious_signals(self):
        out = r.relationship_report(cohort(), top_k=0)
        self.assertEqual(out["relations"]["genre"]["strongest_training_selected_pairs"], [])
        self.assertEqual(out["relations"]["genre"]["undefined_train_spearman_pairs"],
                         23 * 87 - 1)

    def test_spearman_has_average_ranks_and_pearson_is_distinct(self):
        x = [1, 1, 2, 3]
        y = [4, 4, 3, 2]
        self.assertAlmostEqual(r.spearman(x, y), -1.0)
        self.assertEqual(r.spearman([1, 1, 1, 1], y), None)
        self.assertEqual(r.pearson([1, 1, 1, 1], y), None)
        self.assertEqual(r.spearman(x[:3], y[:3]), None)

    def test_no_holdout_is_fatal_even_when_vectors_exist(self):
        rows = cohort(artists=2, per_artist=10)
        # Choosing a single artist per split gives 10 each (valid).
        r.relationship_report(rows)
        # Bridged album group collapses independent sources.
        rows[10]["album_group"] = rows[0]["album_group"]
        with self.assertRaisesRegex(ValueError, "No independent"):
            r.relationship_report(rows)

    def test_small_partitions_or_corrupt_values_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "too few recordings"):
            r.relationship_report(cohort(artists=2, per_artist=3))
        with self.assertRaisesRegex(ValueError, "too few recordings"):
            r.relationship_report(cohort(artists=4, per_artist=2), min_partition=5)
        broken = cohort()
        broken[0]["genre"][0] = 1.2
        with self.assertRaisesRegex(ValueError, "range"):
            r.relationship_report(broken)
        broken = cohort()
        broken[0]["bliss"][4] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            r.relationship_report(broken)
        with self.assertRaises(ValueError):
            r.relationship_report(cohort(), top_k=11)

if __name__ == "__main__":
    unittest.main()
