"""WP1-E5 fictional fixtures; all source names/ratings are synthetic."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_wp1_e4_ccmsim_metadata as e4
import audit_wp1_e5_ccmsim_clip_splits as e5
from test_audit_wp1_e4_ccmsim_metadata import fictional_tables, make_csv


class PinnedClipDisjointFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping_raw,cls.label_raw=fictional_tables()
        cls.mapping=e4.read_csv(cls.mapping_raw,e4.MAPPING_COLUMNS)
        cls.labels=e4.read_csv(cls.label_raw,e4.LABEL_COLUMNS)
        cls.report=e5.build_report(cls.mapping_raw,cls.label_raw)

    def test_primary_clip_partition_and_representative_source_balancing(self):
        report=self.report
        self.assertEqual(report["source_datasets"],9)
        self.assertEqual(report["published_unique_pairs"],1130)
        self.assertEqual(report["annotated_distinct_clips"],463)
        self.assertEqual(report["fixed_seeds"],[3,4,7,13,21])
        self.assertEqual(len(report["results"]),10)
        for result in report["results"]:
            self.assertEqual(sum(result["clip_counts_by_partition"].values()),463)
            self.assertEqual(result["cross_partition_pairs_quarantined"]+
                             result["retained_pairs_total"],1130)
            self.assertTrue(result[
                "all_annotated_clip_ids_appear_in_exactly_one_partition"])
            self.assertTrue(result[
                "all_retained_question_edges_are_clip_disjoint_between_partitions"])
            self.assertFalse(result["original_artist_album_recording_disjointness_verified"])
            self.assertFalse(result["human_scores_used_for_partition"])
            self.assertFalse(result["model_score_calculated"])
            for ds in e4.SOURCES:
                vals=result["per_source_clip_counts_by_partition"][ds]
                self.assertEqual(sum(vals.values()),
                                 sum(1 for x in self.mapping
                                     if x["dataset"]==ds and x["survey_audio_id"] in {
                                         part for r in self.labels
                                         for part in r["audio_pair"].split("-")
                                     }))
                if result["policy"]=="five_disjoint_clip_folds":
                    self.assertLessEqual(max(vals.values())-min(vals.values()),1)
        self.assertEqual(report["primary_test_retained_question_count"],
          report["results"][0]["retained_question_counts_by_partition"]["test"])

    def test_no_leakage_even_for_cross_dataset_song_pairs(self):
        active_by_source={}
        for row in self.labels:
            for id_ in row["audio_pair"].split("-"):
                source=next(m["dataset"] for m in self.mapping
                            if m["survey_audio_id"]==id_)
                active_by_source.setdefault(source,set()).add(id_)
        for result in self.report["results"]:
            assigned,source_counts,slots=e5._assign(
                active_by_source,result["seed"],result["policy"])
            self.assertEqual(len(assigned),463)
            counts={name:0 for name in slots}
            dropped=0
            for row in self.labels:
                a,b=row["audio_pair"].split("-")
                if assigned[a]!=assigned[b]:
                    dropped+=1
                else:
                    counts[assigned[a]]+=1
            self.assertEqual(counts,result["retained_question_counts_by_partition"])
            self.assertEqual(dropped,result["cross_partition_pairs_quarantined"])

    def test_human_label_contents_do_not_affect_partition(self):
        alternate=[dict(x) for x in self.labels]
        for row in alternate:
            row["overall_music_similarity"]="0.125"
            row["cultural_similarity"]="0.975"
            row["recommendation_level"]="0.25"
        altered=e5.build_report(
            self.mapping_raw,make_csv(e4.LABEL_COLUMNS,alternate))
        self.assertEqual(altered,self.report)

    def test_strict_pinned_profile_refuses_deviations(self):
        bad=self.labels[:]
        with self.assertRaises(ValueError):
            e5.build_report(self.mapping_raw,
                            make_csv(e4.LABEL_COLUMNS,bad[:-1]))
        with self.assertRaises(ValueError):
            e5.partition_profile(self.mapping,self.labels[:100],
                                 seed=3,policy=e5.POLICIES[0])
        with self.assertRaises(ValueError):
            e5.partition_profile(self.mapping,self.labels,
                                 seed=100,policy=e5.POLICIES[0])
        with self.assertRaises(ValueError):
            e5.partition_profile(self.mapping,self.labels,
                                 seed=3,policy="optimize-for-test-answers")
        altered=[dict(row) for row in self.labels]
        altered[0]["audio_pair"]="UNMAPPED-ID"
        with self.assertRaises(ValueError):
            e5.partition_profile(self.mapping,altered,
                                 seed=3,policy=e5.POLICIES[0])

    def test_output_contains_no_songs_ratings_or_audio_paths(self):
        serialized=json.dumps(self.report,sort_keys=True)
        for forbidden in (
            "fictional-unpublished-track", "audio_file_path",
            "survey_audio_id","fake00_00", "human_similarity_annotations",
            "overall_music_similarity_annotations",
            "participant_id", "0.975", "source_song_path"
        ):
            self.assertNotIn(forbidden,serialized)
        self.assertFalse(self.report["source_clip_ids_or_pair_ids_or_human_labels_exported"])
        self.assertFalse(self.report["third_party_audio_requested"])
        self.assertFalse(self.report["artist_album_independence_verified"])
        self.assertFalse(self.report["same_recording_essentia_or_bliss_features_computed"])
        self.assertFalse(self.report["any_model_fitted_or_selected"])


if __name__=="__main__":
    unittest.main()
