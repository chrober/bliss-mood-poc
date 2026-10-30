"""WP1-E3: sharp marginal-only MTT paired identifiability regression."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_wp1_e3_paired_bounds as e3


def synthetic_verified_aggregate():
    from audit_wp1_external_aggregates import (
        SCHEMA, MTT_BASE, MTT_LOCAL,
    )
    method_names=MTT_BASE+MTT_LOCAL
    counts={
        "embedding_cosine": 182,
        "genre_cosine":191, "mood_cosine":192,
        "genre_centered_cosine":191,"mood_centered_cosine":193,
        "rank_audio_genre_equal":163,
        "rank_audio_mood_equal":170,
        "rank_genre_mood_equal":167,
        "rank_audio_genre_mood_equal":192,
    }
    methods={}
    for name in method_names:
        methods[name]={
            "correct":counts[name],"predicted":293,
            "undefined":0,"metric_ties":0,"scorable":293,
        }
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_HISTORICAL_PUBLIC_AGGREGATES_NO_NEW_AUDIO_OR_FUSION",
        "evidence":{
            "mtt":{
                "decisive_questions":293,"questions_total":346,
                "same_question_audio_paired":True,
                "global_pairwise_fusions_measured":False,
                "methods":methods,
            },
            "fma":{"sample_songs":80,"official_split":"validation",
                   "untouched_official_test":True},
            "deam":{"sample_songs":240},
        },
        "sources":{k:{"member_sha256": "abcdef"+k}
                   for k in ("mtt","fma","deam")},
    }


class SharpPairedBoundsTests(unittest.TestCase):
    def test_exact_all_feasible_joint_tables_without_guessing_one(self):
        self.assertEqual(list(e3.sharp_tables(3,2,1)),[
            (0,2,1,0),(1,1,0,1)])
        out=e3.comparison(293,193,192)
        self.assertEqual((out["sharp_feasible_discordant_questions_min"],
                          out["sharp_feasible_discordant_questions_max"]),(1,201))
        self.assertEqual(out["reference_minus_candidate_correct"],1)
        self.assertEqual(out["sharp_feasible_both_correct_min"],92)
        self.assertEqual(out["sharp_feasible_both_correct_max"],192)
        self.assertEqual(out["hypothetical_joint_tables"],101)
        self.assertFalse(out["actual_p_value_estimable"])
        self.assertFalse(out["paired_confidence_interval_estimable"])

    def test_exact_p_computations_are_hypothetical_only(self):
        self.assertEqual(e3.exact_mcnemar_p(0,0),1)
        self.assertEqual(e3.exact_mcnemar_p(1,0),1)
        self.assertAlmostEqual(e3.exact_mcnemar_p(10,0), 2/1024)
        self.assertEqual(e3.exact_mcnemar_p(4,4),1)
        self.assertEqual(e3.exact_mcnemar_p(0,4),
                         e3.exact_mcnemar_p(4,0))
        with self.assertRaises(ValueError):
            e3.exact_mcnemar_p(-1,3)
        with self.assertRaises(ValueError):
            e3.exact_mcnemar_p(True,3)

    def test_feasible_marginal_bounds_are_mathematically_sharp(self):
        for n in range(1,9):
            for a in range(n+1):
                for b in range(n+1):
                    tables=list(e3.sharp_tables(n,a,b))
                    actual={(sum(1 for x,y in mask if x and y),
                             sum(1 for x,y in mask if x and not y),
                             sum(1 for x,y in mask if not x and y),
                             sum(1 for x,y in mask if not x and not y))
                            for mask in __import__("itertools").product(
                                ((0,0),(0,1),(1,0),(1,1)), repeat=n)
                            if sum(x for x,y in mask)==a
                            and sum(y for x,y in mask)==b} if n<=5 else None
                    for both,only_a,only_b,neither in tables:
                        self.assertEqual(both+only_a,a)
                        self.assertEqual(both+only_b,b)
                        self.assertEqual(sum((both,only_a,only_b,neither)),n)
                        if actual is not None:
                            self.assertIn((both,only_a,only_b,neither),actual)

    def test_all_historical_mtt_contrasts_same_denominator_no_fake_paired_test(self):
        fake=synthetic_verified_aggregate()
        report=e3.report_from_verified_e1(fake)
        self.assertEqual(report["status"],
          "SHARP_MARGINAL_BOUNDS_ONLY_NO_OBSERVED_PAIRED_TEST")
        self.assertEqual(len(report["contrasts"]),8)
        self.assertEqual(report["mtt_human_questions_decisive"],293)
        self.assertTrue(report["all_question_level_joint_correctness_values_missing"])
        self.assertTrue(report["no_observed_mcnemar_test_or_paired_bootstrap_claimed"])
        self.assertFalse(report["general_metric_selected"])
        self.assertFalse(report["other_tasks"]["fma"][
            "query_level_paired_inference_identifiable"])
        self.assertTrue(report["other_tasks"]["fma"]["official_test_untouched"])
        self.assertFalse(report["other_tasks"]["deam"][
            "query_level_paired_inference_identifiable"])
        contrast=report["contrasts"]["mood_cosine"]
        self.assertEqual(contrast["reference_minus_candidate_correct"],1)
        self.assertEqual(contrast["sharp_feasible_discordant_questions_max"],201)
        for method in report["contrasts"].values():
            self.assertEqual(method["common_question_denominator"],293)
            self.assertFalse(method["actual_p_value_estimable"])
            self.assertTrue(method["actual_joint_correctness_unavailable"])
        self.assertNotIn("fictional-user",json.dumps(report))

    def test_fail_closed_on_changed_provenance_coverage_or_methods(self):
        import copy
        base=synthetic_verified_aggregate()
        changes=[
            lambda x:x.update(status="NOT_VERIFIED"),
            lambda x:x["evidence"]["mtt"].update(decisive_questions=294),
            lambda x:x["evidence"]["mtt"].update(same_question_audio_paired=False),
            lambda x:x["evidence"]["mtt"].update(global_pairwise_fusions_measured=True),
            lambda x:x["evidence"]["mtt"]["methods"]["mood_cosine"].update(scorable=292),
            lambda x:x["evidence"]["mtt"]["methods"]["mood_cosine"].update(predicted=292),
            lambda x:x["evidence"]["fma"].update(untouched_official_test=False),
            lambda x:x["evidence"]["deam"].update(sample_songs=10),
            lambda x:x["evidence"]["mtt"]["methods"].pop("embedding_cosine"),
        ]
        for change in changes:
            test=copy.deepcopy(base)
            change(test)
            with self.subTest(change=change),self.assertRaises(ValueError):
                e3.report_from_verified_e1(test)
        for bad in ((293,-1,10),(293,1,294),(0,0,0),(293,True,1)):
            with self.assertRaises(ValueError):
                list(e3.sharp_tables(*bad))


if __name__=="__main__":
    unittest.main()
