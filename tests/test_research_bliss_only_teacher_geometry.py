"""Synthetic Bliss-only student retrieval geometry versus Essentia pseudo-teacher."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from research_bliss_only_teacher_geometry import proxy_geometry_report


def songs(artists=16, per_artist=6):
    rows=[]
    for artist in range(artists):
        for index in range(per_artist):
            n=artist*per_artist+index
            x0=.05+.9*n/(artists*per_artist+1)
            x1=.5+.4*math.sin(.51*n)
            x2=.5+.4*math.cos(.31*n)
            x=[x0,x1,x2]+[.3+.01*((artist+index+k*3)%17) for k in range(20)]
            rows.append({
                "track_id":f"Secret Music / Artist {artist} / Song {index}",
                "artist_group":f"Artist-Group-{artist}",
                "album_group":f"Album-Group-{artist}",
                "recording_group":f"Recording-Group-{artist}-{index}",
                "bliss":x,
                "genre":[.1+.6*x0,.15+.7*x1,.12+.6*x2]+[.4]*84,
                "moodtheme":[.7-.5*x0,.2+.6*x1,.3+.5*x2]+[.3]*53,
            })
    return rows


class BlissStudentGeometryTests(unittest.TestCase):
    def test_student_uses_only_bliss_at_inference_and_reports_grouped_proxy(self):
        data=proxy_geometry_report(songs(),seed=20261029)
        self.assertEqual(data["train_songs"]+
                         data["all_group_disjoint_outer_holdout_songs"],96)
        self.assertTrue(data["guarantees"]["Ridge_and_Bliss_scaler_fitted_on_train_only"])
        self.assertFalse(data["teacher_head_needed_at_student_inference"])
        self.assertEqual(data["input_at_student_inference"],"Bliss_23D_only")
        for head in ("genre","moodtheme"):
            metrics=data["methods"][head]
            student=metrics["heldout_spearman_teacher_vs_bliss_only_ridge_student_euclidean"]
            self.assertIsNotNone(student)
            self.assertGreater(student,.2)
            self.assertIsNotNone(metrics[
                "heldout_spearman_teacher_vs_train_standardized_bliss_euclidean"])
            self.assertIsNotNone(metrics[
                "heldout_spearman_teacher_vs_permuted_teacher_negative_control"])
        self.assertEqual(data,proxy_geometry_report(songs(),seed=20261029))
        rendered=json.dumps(data)
        for secret in ("Secret Music","Artist-Group","Recording-Group"):
            self.assertNotIn(secret,rendered)

    def test_entangled_sources_fail(self):
        rows=songs(artists=4,per_artist=8)
        for row in rows:
            row["album_group"]="Shared Album"
        with self.assertRaisesRegex(ValueError,"No independent"):
            proxy_geometry_report(rows)

    def test_missing_head_or_invalid_regularizer_fails(self):
        rows=songs()
        rows[0]["genre"][0]=float("inf")
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            proxy_geometry_report(rows)
        with self.assertRaises(ValueError):
            proxy_geometry_report(songs(),ridge_alpha=-1.0)

    def test_full_pair_count_is_bounded(self):
        out=proxy_geometry_report(songs(artists=40,per_artist=7))
        self.assertLessEqual(out["heldout_songs_for_pairs"],80)
        self.assertEqual(out["holdout_unique_unordered_pairs"],
                         out["heldout_songs_for_pairs"]*
                         (out["heldout_songs_for_pairs"]-1)//2)

if __name__=="__main__":
    unittest.main()
