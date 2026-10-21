"""Deterministic paired metric sensitivity, no per-song outputs."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("paired", ROOT / "mtt_paired_evidence.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PairedMTTTests(unittest.TestCase):
    def cohort(self):
        rows = []
        for i in range(36):
            # Two comparison metrics on identical questions, some shared artists.
            rows.append({
                "outcomes": {
                    "alpha": 1 if i < 27 else 0,
                    "beta": 1 if i < 18 else 0,
                    "gamma": 1 if i >= 18 else 0
                },
                "artists": ["artist " + str(i // 6), "other "+str(i % 8)],
            })
        return rows

    def test_paired_identical_seed_reproduces_and_excludes_ids(self):
        a=m.paired_sensitivity(self.cohort(),["alpha","beta","gamma"],
                               seed=20261021,replicates=120)
        b=m.paired_sensitivity(self.cohort(),["alpha","beta","gamma"],
                               seed=20261021,replicates=120)
        self.assertEqual(a,b)
        self.assertEqual(a["comparison_count"],3)
        self.assertEqual(a["common_human_scorable_questions"],36)
        self.assertEqual(a["paired_comparisons"][0]["a_only_correct"],9)
        self.assertEqual(a["paired_comparisons"][0]["b_only_correct"],0)
        self.assertAlmostEqual(a["paired_comparisons"][0]["paired_accuracy_delta_pp"],25)
        self.assertIn("CI", a["limits"][2])
        serialized=str(a)
        self.assertNotIn("artist 0",serialized)
        self.assertNotIn("other 0",serialized)

    def test_coverage_and_invalid_data_are_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"common reference"):
            m.paired_sensitivity([{"outcomes":{"alpha":1},
                                   "artists":["a"]}],
                                 ["alpha","beta"],replicates=120)
        with self.assertRaisesRegex(ValueError,"metadata"):
            m.paired_sensitivity([{"outcomes":{"alpha":1,"beta":0},
                                   "artists":[]}],
                                 ["alpha","beta"],replicates=120)
        with self.assertRaisesRegex(ValueError,"0/1"):
            m.paired_sensitivity([{"outcomes":{"alpha":.5,"beta":0},
                                   "artists":["a"]}],
                                 ["alpha","beta"],replicates=120)
        with self.assertRaisesRegex(ValueError,"100"):
            m.paired_sensitivity(self.cohort(),["alpha","beta"],replicates=1)

    def test_quantile_boundary_is_correct(self):
        self.assertEqual(m.quantile([1,2,3],0),1)
        self.assertEqual(m.quantile([1,2,3],1),3)
        self.assertEqual(m.quantile([1,2,3],.5),2)


if __name__=="__main__":
    unittest.main()
