"""Synthetic-only WP1-E1 immutable public aggregate audit tests (no audio)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_wp1_external_aggregates as wp1


class PublicAggregateAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fictional-wp1-e1-")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = {
            "mtt": {"member": "mtt.json", "question_count": 346,
                    "decisive_count": 293, "unique_clips": 1019,
                    "task": "human_odd_one_out_majority"},
            "fma": {"member": "fma.json", "sample_songs": 80,
                    "distinct_artists": 80, "sample_id_sha256": "fake-fma",
                    "task": "coarse_genre_retrieval_validation"},
            "deam": {"member": "deam.json", "sample_songs": 240,
                     "sample_id_sha256": "fake-deam",
                     "task": "human_valence_arousal_proximity_proxy"},
        }
        self.data = {
            "mtt": {
                "status": "EXPLORATORY_346_MTT_NO_UNSEEN_HOLDOUT",
                "total_unique_triplets": 346, "human_scorable_triplets": 293,
                "unique_clips": 1019, "human_ties": 53,
                "paired_same_audio_and_questions": True,
                "representation_comparison":
                    "fixed_equal_rank_fusions_with_audio_genre_mood_baselines",
                "fixed_rank_fusions": {"triplet_local": True,
                                       "no_label_fit": True},
                "methods": {method: {
                    "correct": 193, "predicted": 293, "undefined": 0,
                    "metric_ties": 0, "human_scorable_questions": 293,
                    "prediction_coverage": 1.0,
                    "accuracy_with_abstentions_as_incorrect": 193 / 293
                } for method in wp1.MTT_BASE + wp1.MTT_LOCAL},
            },
            "fma": {
                "schema": "fma-catalog-screened-80-embedding-vs-heads-v1",
                "status": "FMA_VALIDATION_EXPLORATORY_NOT_INDEPENDENT_HOLDOUT",
                "official_split": "validation", "sample_size": 80,
                "distinct_artists": 80, "sample_id_sha256": "fake-fma",
                "methods": {method: {
                    "full_queries": 80, "abstained_queries": 0,
                    "query_denominator": 80, "query_coverage": 1.0,
                    "precision_at_5": .3, "map_at_10": .2, "ndcg_at_10": .4
                } for method in wp1.FMA_METHODS},
            },
            "deam": {
                "schema": "deam-similarity-benchmark-v1",
                "dataset": {
                    "songs_evaluated": 240, "sample_id_sha256": "fake-deam",
                    "annotation_cohort_counts": {
                        "earlier_excerpt": 197, "full_song_2015": 43}},
                "per_head": {"moodtheme": {
                    method: {"axes": {"valence_arousal": {
                        "query_count": 240, "mean_query_spearman": .28}}}
                    for method in wp1.DEAM_METHODS}},
            },
        }
        self.lock = {
            "schema": "wp1-e1-external-aggregate-lock-v1",
            "artifacts": self.source,
            "unmeasured": {"mtt_global_pairwise_equal_weight_fusions": {
                "method_ids": list(wp1.GLOBAL_METHODS)}},
        }
        self.paths = {}
        for key in wp1.KEYS:
            raw = json.dumps(self.data[key]).encode("utf-8")
            self.source[key]["member_sha256"] = hashlib.sha256(raw).hexdigest()
            self.source[key]["run_id"] = 100 + len(self.paths)
            self.source[key]["artifact_id"] = 200 + len(self.paths)
            dest = self.folder / (key + ".zip")
            with zipfile.ZipFile(dest, "w") as z:
                z.writestr(self.source[key]["member"], raw)
            self.paths[key] = dest

    def test_separate_tasks_full_coverage_and_unmeasured_fusions(self):
        result = wp1.audit(self.lock, self.paths)
        self.assertEqual(result["status"],
            "VERIFIED_HISTORICAL_PUBLIC_AGGREGATES_NO_NEW_AUDIO_OR_FUSION")
        self.assertFalse(result["cross_task_score_averaged"])
        self.assertFalse(result["unmeasured_global_fusions_imputed"])
        self.assertFalse(result["evidence"]["mtt"]["global_pairwise_fusions_measured"])
        self.assertEqual(result["evidence"]["mtt"]["methods"]
                         ["mood_centered_cosine"]["scorable"], 293)
        self.assertEqual(result["evidence"]["fma"]["sample_songs"], 80)
        self.assertEqual(result["evidence"]["deam"]["sample_songs"], 240)
        self.assertEqual(result["feature_coverage"]["mtt"]["bliss23"],
                         "NOT_VERIFIED")

    def test_zip_member_tamper_rejected(self):
        with zipfile.ZipFile(self.paths["mtt"], "w") as z:
            z.writestr("mtt.json", b'{"tampered":true}')
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            wp1.audit(self.lock, self.paths)

    def test_global_fusion_injected_into_mtt_is_not_misreported(self):
        self.data["mtt"]["methods"]["global_genre_mood_equal"] = (
            self.data["mtt"]["methods"]["mood_cosine"])
        with self.assertRaisesRegex(ValueError, "inventory"):
            wp1._mtt(self.data["mtt"], self.source["mtt"])

    def test_mtt_abstention_is_not_selectively_discarded(self):
        row = self.data["mtt"]["methods"]["rank_audio_genre_equal"]
        row.update(correct=150, predicted=230, metric_ties=63,
                   prediction_coverage=230 / 293,
                   accuracy_with_abstentions_as_incorrect=150 / 293)
        result = wp1._mtt(self.data["mtt"], self.source["mtt"])
        self.assertEqual(result["methods"]["rank_audio_genre_equal"]["scorable"],
                         293)
        row["accuracy_with_abstentions_as_incorrect"] = 150 / 230
        with self.assertRaisesRegex(ValueError, "denominator"):
            wp1._mtt(self.data["mtt"], self.source["mtt"])

    def test_fma_test_split_or_fma_provenance_rejected(self):
        self.data["fma"]["official_split"] = "test"
        with self.assertRaisesRegex(ValueError, "official_split"):
            wp1._fma(self.data["fma"], self.source["fma"])
        self.data["fma"]["official_split"] = "validation"
        self.data["fma"]["sample_id_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "sample_id_sha256"):
            wp1._fma(self.data["fma"], self.source["fma"])

    def test_deam_incomplete_sample_rejected(self):
        self.data["deam"]["dataset"]["annotation_cohort_counts"] = {
            "earlier_excerpt": 198, "full_song_2015": 42}
        with self.assertRaisesRegex(ValueError, "strata"):
            wp1._deam(self.data["deam"], self.source["deam"])

    def test_cross_dataset_comparison_not_collapsed_to_one_number(self):
        out = wp1.audit(self.lock, self.paths)
        self.assertEqual(set(out["evidence"]), {"mtt", "fma", "deam"})
        self.assertNotIn("overall_accuracy", out)
        self.assertNotIn("best_general_metric", out)


if __name__ == "__main__":
    unittest.main()
