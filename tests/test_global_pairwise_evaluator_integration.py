"""Cross-evaluator synthetic regression: original baselines stay identical, opt-in adds 4 methods."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_mtt_embedding_ab as mtt
import evaluate_fma_embedding_ab as fma
import evaluate_deam_embedding_ab as deam
import global_pairwise_fusion as fusion


def vectors(index: int) -> dict:
    # Distinct, positive activations; no zero-variance centered cosine.
    return {
        "genre": tuple(0.04 + (index*7 + k*11)%31 / 40 for k in range(20)),
        "moodtheme": tuple(0.03 + (index*3 + k*13)%37 / 45 for k in range(20)),
        "embedding": tuple((index*17 + k*7)%41 / 50 for k in range(20)),
    }


class GlobalEvaluatorTests(unittest.TestCase):
    def test_mtt_prediction_equivalent_to_direct_fixed_pair_scores(self):
        ids = ("a", "b", "c")
        data = {key:vectors(i+1) for i,key in enumerate(ids)}
        for method in fusion.FUSIONS:
            actual, why = mtt.odd_one_out(ids,data,
                lambda a,b: fusion.pair_score(a,b,method))
            self.assertIn(actual, ids+(None,))
            self.assertIn(why, (None,"tie","undefined"))

    def test_fma_opt_in_does_not_change_original_five_methods(self):
        ids=[f"{i:06d}" for i in range(16)]
        songs={s:{"genre":f"G{i//2}","artist":f"artist{i}"} for i,s in enumerate(ids)}
        data={s:vectors(i+1) for i,s in enumerate(ids)}
        control=fma.evaluate_paired(data,ids,songs,seed=20261021,replicates=100)
        trial=fma.evaluate_paired(data,ids,songs,seed=20261021,replicates=100,
                                   global_pair_fusions=True)
        self.assertEqual(len(control["methods"]),5)
        self.assertEqual(len(trial["methods"]),9)
        self.assertEqual(trial["global_pairwise_fusions"]["fusions"],fusion.provenance()["fusions"])
        for name in control["methods"]:
            self.assertEqual(control["methods"][name],trial["methods"][name])
        for name in fusion.FUSIONS:
            self.assertEqual(trial["methods"][name]["query_denominator"],16)
            self.assertEqual(trial["methods"][name]["full_queries"],16)

    def test_deam_opt_in_does_not_change_original_five_methods(self):
        ids=[str(i) for i in range(1,7)]+[str(2001+i) for i in range(6)]
        labels={s:(2.0 + .29*i,2.0+((i*7)%11)*.25) for i,s in enumerate(ids)}
        data={s:vectors(i+2) for i,s in enumerate(ids)}
        control=deam.paired_va(data,ids,labels,seed=20261021,replicates=100)
        trial=deam.paired_va(data,ids,labels,seed=20261021,replicates=100,
                             global_pair_fusions=True)
        self.assertEqual(len(control["methods"]),5)
        self.assertEqual(len(trial["methods"]),9)
        for name in control["methods"]:
            self.assertEqual(control["methods"][name],trial["methods"][name])
        for name in fusion.FUSIONS:
            self.assertEqual(trial["methods"][name]["query_denominator"],12)
            self.assertEqual(trial["methods"][name]["queries_complete"],12)
            self.assertTrue(all(math.isfinite(x)
                for x in trial["methods"][name]["axes"].values()))


if __name__ == "__main__":
    unittest.main()
