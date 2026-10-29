"""WP3-R2 synthetic, source-grouped sklearn teacher-model contracts."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_bliss_essentia_teacher_models as model


def synthetic(artists=14, per_artist=5):
    songs=[]
    for group in range(artists):
        for j in range(per_artist):
            n=group*per_artist+j
            x0=0.05+0.85*n/max(1,artists*per_artist)
            x1=0.5+0.4*math.sin(n*.7)
            x2=0.5+0.4*math.cos(n*.47)
            values=[x0,x1,x2]+[.05+.01*((3*j+k*group)%31) for k in range(20)]
            genre=[.15+.6*x0,.2+.55*x1,.17+.65*x2]+[.4]*84
            mood=[.75-.5*x0,.18+.6*x1,.2+.5*x2]+[.3]*53
            songs.append({
                "track_id":f"Private Song {group}/{j}",
                "artist_group":f"private-artist-{group}",
                "album_group":f"private-album-{group}",
                "recording_group":f"private-recording-{group}-{j}",
                "bliss":values,"genre":genre,"moodtheme":mood,
            })
    return songs


class TeacherModelsTests(unittest.TestCase):
    def test_fixed_train_only_ridge_pls_pca_cca_teacher_report(self):
        rows=synthetic()
        result=model.model_report(rows,seed=20261029)
        self.assertEqual(result["train_songs"]+result["holdout_songs"],len(rows))
        self.assertTrue(result["guarantees"]["fit_scaler_ridge_pls_pca_cca_only_on_train"])
        self.assertTrue(result["guarantees"]["musical_similarity_not_assessed"])
        for head,dimensions in (("genre",87),("moodtheme",56)):
            method=result["methods"][head]
            self.assertEqual(method["teacher_dimensions"],dimensions)
            self.assertGreater(method["constant_predictor_train_mean_mae"],0)
            self.assertLess(method["ridge_train_only_holdout_mae"],
                            method["constant_predictor_train_mean_mae"])
            self.assertTrue(math.isfinite(method["pls_train_only_holdout_mae"]))
            self.assertEqual(len(method["cca_heldout_canonical_pearson"]),1)
            self.assertTrue(method["cca_heldout_canonical_pearson"][0] is None or
                            -1 <= method["cca_heldout_canonical_pearson"][0] <= 1)
        self.assertEqual(result,model.model_report(rows,seed=20261029))
        rendered=json.dumps(result)
        for secret in ("Private Song","private-artist","private-recording"):
            self.assertNotIn(secret,rendered)

    def test_no_valid_group_holdout_fails_closed(self):
        rows=synthetic(artists=4,per_artist=5)
        for row in rows:
            row["album_group"]="same-release"
        with self.assertRaisesRegex(ValueError,"No independent"):
            model.model_report(rows)

    def test_insufficient_training_rank_fails_closed(self):
        rows=synthetic()
        for row in rows:
            row["bliss"]=[0.25]*23
        with self.assertRaisesRegex(ValueError,"Insufficient independent Bliss"):
            model.model_report(rows)

    def test_bad_dimensions_nonfinite_or_hyperparameters_fail(self):
        rows=synthetic()
        with self.assertRaises(ValueError):
            model.model_report(rows,pls_components=0)
        with self.assertRaises(ValueError):
            model.model_report(rows,ridge_alpha=0.0)
        with self.assertRaises(ValueError):
            model.model_report(rows,cca_components=3)
        broken=synthetic()
        broken[0]["moodtheme"][1]=float("nan")
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            model.model_report(broken)

if __name__=="__main__":
    unittest.main()
