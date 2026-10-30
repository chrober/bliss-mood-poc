"""WP2-P4 synthetic four-way group-gated score-calibration research tests."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_personal_synthetic_calibration as c
from research_personal_synthetic_metric_learning import (
    DIM, SEED, Model, fictional_cohort, fit,
)


class FictionalCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=c.run()

    def test_four_way_artist_album_recording_and_triplet_family_disjoint(self):
        for scenario in ("axis_sparse","cross_feature"):
            triplets,features,metadata=fictional_cohort(SEED,scenario)
            partitions=c.split_four_ways(triplets,metadata)
            self.assertEqual({key:len(val) for key,val in partitions.items()},
                             {"train":192,"calibration":48,
                              "validation":48,"test":96})
            sets={}
            for name,indices in partitions.items():
                sets[name]={track for i in indices for track in triplets[i]}
            for a in sets:
                for b in sets:
                    if a==b:
                        continue
                    self.assertFalse(sets[a]&sets[b])
                    for field in ("artist_group","album_group","recording_group"):
                        self.assertFalse(
                            {metadata[k][field] for k in sets[a]} &
                            {metadata[k][field] for k in sets[b]})
            self.assertEqual(len({i for v in partitions.values() for i in v}),
                             len(triplets))
            for part in ("calibration","validation","test"):
                pairs=c.group_pairs(triplets,features,metadata,
                                    partitions[part],scenario)
                self.assertEqual(len(pairs),
                                 {"calibration":90,"validation":90,
                                  "test":180}[part])
                self.assertEqual(len({tuple(sorted((a,b))) for a,b,_ in pairs}),
                                 len(pairs))

    def test_calibrator_monotonicity_scale_and_invalid_refusal(self):
        obs=[(float(i),int(i<25)) for i in range(1,65)]
        mapper=c.calibrate(obs)
        self.assertGreater(mapper.predict(1),mapper.predict(60))
        self.assertGreaterEqual(mapper.predict(60),0)
        self.assertLessEqual(mapper.predict(1),1)
        self.assertEqual(mapper.digest(),mapper.digest())
        for samples in (
            [],[(1.,1)]*80,[(1.,0)]*80,
            [(1.,1)]*7+[(1.,0)]*70,
            [(float("nan"),0)]*80,
            [(-0.01,0)]*80,
        ):
            with self.subTest(sample=samples[:1]):
                with self.assertRaises(ValueError):
                    c.calibrate(samples)
        for d in (-1.,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                mapper.predict(d)
        with self.assertRaises(ValueError):
            c.Calibrator(0.,1.,2.)
        with self.assertRaises(ValueError):
            c.Calibrator(1.,1.,-2.)

    def test_validation_gate_thresholds_and_class_support(self):
        passed={"pair_count":90,"positive_count":35,
                "brier":0.15,"ece_5_equal_width_bins":0.12}
        self.assertTrue(c.validation_gate(passed))
        for item,value in [
            ("brier",0.25),("ece_5_equal_width_bins",0.25),
            ("positive_count",7),("pair_count",50)
        ]:
            bad=dict(passed);bad[item]=value
            self.assertFalse(c.validation_gate(bad))

    def test_training_and_calibrator_do_not_read_sealed_test_labels(self):
        triple,features,metadata=fictional_cohort(SEED,"axis_sparse")
        partitions=c.split_four_ways(triple,metadata)
        original=fit(triple,features,partitions["train"][:25],
                     capacity="diagonal",seed=SEED+3)
        changed=list(triple)
        for i in partitions["test"]:
            a,b,odd=changed[i]
            changed[i]=(a,odd,b)
        after=fit(changed,features,partitions["train"][:25],
                  capacity="diagonal",seed=SEED+3)
        self.assertEqual(original,after)
        orig_cal=c.group_pairs(triple,features,metadata,
                               partitions["calibration"],"axis_sparse")
        changed_cal=c.group_pairs(changed,features,metadata,
                                  partitions["calibration"],"axis_sparse")
        self.assertEqual(orig_cal,changed_cal)
        self.assertEqual(
            c.calibrate(c.distances(orig_cal,features,original)).digest(),
            c.calibrate(c.distances(changed_cal,features,after)).digest())

    def test_five_blends_are_exact_general_if_uncertified(self):
        triple,features,metadata=fictional_cohort(SEED,"axis_sparse")
        partitions=c.split_four_ways(triple,metadata)
        general=Model((1.,)*DIM)
        personal=Model((2.,)*DIM)
        pairs=c.group_pairs(triple,features,metadata,
                            partitions["calibration"],"axis_sparse")
        gen_map=c.calibrate(c.distances(pairs,features,general))
        per_map=c.calibrate(c.distances(pairs,features,personal))
        off=c.score_triplets(triple,features,partitions["test"],
                             general,personal,gen_map,per_map,False)
        self.assertEqual(set(off),{"0","25","50","75","100"})
        for p in (25,50,75,100):
            self.assertEqual(off[str(p)]["accuracy"],off["0"]["accuracy"])
            self.assertEqual(off[str(p)]["fallback_queries"],96)
            self.assertEqual(off[str(p)]["effective_personal_percent"],0)
        on=c.score_triplets(triple,features,partitions["test"],
                            general,personal,gen_map,per_map,True)
        self.assertEqual(on["0"]["accuracy"],off["0"]["accuracy"])
        self.assertEqual(on["100"]["effective_personal_percent"],100)
        self.assertEqual(on["100"]["fallback_queries"],0)

    def test_report_provenance_scope_denominators_and_privacy(self):
        r=self.report
        self.assertEqual(r["schema"],c.SCHEMA)
        self.assertFalse(r["test_used_to_fit_or_select_model"])
        self.assertFalse(r["real_calibration_or_music_similarity_certified"])
        self.assertFalse(r["personal_model_eligible_for_runtime_activation"])
        self.assertFalse(r["general_metric_selected"])
        self.assertFalse(r["actual_calibration_parameters_or_personal_weights_exported"])
        for scenario in r["scenarios"].values():
            self.assertEqual(scenario["split_triplet_counts"],
                             {"train":192,"calibration":48,
                              "validation":48,"test":96})
            self.assertEqual(scenario["calibration_pairs_per_model"],90)
            self.assertEqual(scenario["validation_pairs_per_model"],90)
            self.assertEqual(scenario["test_pairs_per_model"],180)
            for method in scenario["learned_candidates"].values():
                self.assertEqual(method["sealed_test_pair_reliability"]["pair_count"],180)
                for key,item in method["sealed_test_blend"].items():
                    self.assertEqual(item["denominator"],96)
                    self.assertEqual(item["effective_personal_percent"],
                                     int(key) if method["fictional_validation_gate_passed"]
                                     else 0)
                    self.assertEqual(item["accuracy"],
                                     round(item["correct"]/96,8))
        raw=json.dumps(r,sort_keys=True)
        for forbidden in ("fictional-artist-","fictional-recording-",
                          "fictional-000-","matrix_weights","private_song"):
            self.assertNotIn(forbidden,raw)


if __name__=="__main__":
    unittest.main()
