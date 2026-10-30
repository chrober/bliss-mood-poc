"""Synthetic invariants for offline, shadow-only Lyrion integration rehearsal."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research_lyrion_general_shadow_contract import (
    SCHEMA, shadow_batch,
)


def fixture(n=6):
    scores = [0.65, 0.95, 0.30, 0.85, 0.45, 0.10]
    return {
        "schema": SCHEMA,
        "mode": "shadow_only",
        "scorer_fingerprint": "fictional-general-fingerprint-v0",
        "score_scale_id": "fictional-frozen-bounded-score-v0",
        "score_orientation": "higher_is_more_similar",
        "experimental_preview_opt_in": False,
        "candidates": [
            {
                "candidate_id": f"private-fake-song-{i}",
                "bliss_rank": i,
                "admitted_by_bliss": True,
                "identity_exact": True,
                "feature_present": True,
                "feature_fingerprint": "fictional-general-fingerprint-v0",
                "essentia_validated": True,
                "general_score": scores[i],
            }
            for i in range(n)
        ],
    }


class LyrionShadowContractTests(unittest.TestCase):
    def test_full_batch_shadow_has_no_mutation_and_aggregate_deltas_only(self):
        source = fixture()
        before = copy.deepcopy(source)
        result = shadow_batch(source)
        self.assertEqual(source, before)
        self.assertEqual(result["status"], "SHADOW_REORDERING_SUMMARY_ONLY")
        self.assertEqual(result["candidate_pool_size"], 6)
        self.assertEqual(result["changed_positions"], 6)
        self.assertEqual(result["top5_overlap"], 4)
        self.assertEqual(result["max_absolute_rank_shift"], 3)
        self.assertTrue(result["bliss_reference_order_unchanged"])
        self.assertTrue(result["candidate_pool_admission_unchanged"])
        self.assertFalse(result["playlist_queue_or_route_writes"])
        self.assertFalse(result["general_metric_validated_or_selected"])
        self.assertFalse(result["personal_metric_activated"])
        self.assertFalse(result["provider_spi_implemented"])
        self.assertFalse(result["score_blending_with_existing_bliss_implemented"])
        message=json.dumps(result)
        self.assertNotIn("private-fake-song", message)
        self.assertNotIn("fictional-general-fingerprint", message)
        self.assertNotIn("general_score", message)
        self.assertNotIn("candidate_id", message)

    def test_any_missing_evidence_falls_back_for_complete_pool(self):
        changes=[
            ("admitted_by_bliss",False,"host_admission_violation"),
            ("identity_exact",False,"exact_track_join_missing"),
            ("feature_present",False,"missing_feature_row"),
            ("feature_fingerprint","incompatible","model_fingerprint_mismatch"),
            ("essentia_validated",False,"source_parity_unvalidated"),
            ("general_score",None,"missing_or_invalid_bounded_general_score"),
            ("general_score",float("nan"),"missing_or_invalid_bounded_general_score"),
            ("general_score",1.01,"missing_or_invalid_bounded_general_score"),
            ("general_score",-0.1,"missing_or_invalid_bounded_general_score"),
        ]
        for field,value,expected in changes:
            with self.subTest(field=field,value=str(value)):
                source=fixture()
                source["candidates"][2][field]=value
                result=shadow_batch(source)
                self.assertEqual(result["status"],
                                 "NEUTRAL_SHADOW_NO_COMPARABLE_FULL_BATCH")
                self.assertIn(expected, result["neutral_fallback_reasons"])
                self.assertFalse(result["shadow_reranking_eligible"])
                self.assertEqual(result["changed_positions"],0)
                self.assertIsNone(result["top5_overlap"])
                self.assertFalse(result["playlist_queue_or_route_writes"])

    def test_explicit_research_optin_allows_unvalidated_preview_only(self):
        source=fixture()
        source["candidates"][4]["essentia_validated"]=False
        source["experimental_preview_opt_in"]=True
        result=shadow_batch(source)
        self.assertEqual(result["status"],"SHADOW_REORDERING_SUMMARY_ONLY")
        self.assertTrue(result["experimental_unvalidated_data_opt_in"])
        self.assertFalse(result["playlist_queue_or_route_writes"])
        self.assertFalse(result["general_metric_validated_or_selected"])
        self.assertFalse(result["provider_spi_implemented"])

    def test_ties_preserve_bliss_order_when_comparing_same_pool(self):
        source=fixture()
        for item in source["candidates"]:
            item["general_score"]=0.5
        result=shadow_batch(source)
        self.assertEqual(result["changed_positions"],0)
        self.assertEqual(result["top5_overlap"],5)
        self.assertEqual(result["max_absolute_rank_shift"],0)

    def test_reject_identity_rank_mutation_unbounded_and_non_shadow_mode(self):
        mutations=[
            lambda q:q.update(mode="apply_to_player"),
            lambda q:q.update(schema="unknown"),
            lambda q:q.update(score_orientation="lower_is_better"),
            lambda q:q.update(experimental_preview_opt_in="true"),
            lambda q:q.update(untrusted_provider_executable="/bin/sh"),
            lambda q:q["candidates"][1].update(candidate_id="private-fake-song-0"),
            lambda q:q["candidates"][1].update(bliss_rank=0),
            lambda q:q["candidates"][1].update(bliss_rank=0.5),
            lambda q:q["candidates"][1].update(identity_exact="true"),
            lambda q:q.update(candidates=q["candidates"][:1]),
            lambda q:q.update(candidates=q["candidates"]*9),
        ]
        for mutate in mutations:
            with self.subTest(mutate=str(mutate)):
                source=fixture()
                mutate(source)
                with self.assertRaises(ValueError):
                    shadow_batch(source)


if __name__ == "__main__":
    unittest.main()
