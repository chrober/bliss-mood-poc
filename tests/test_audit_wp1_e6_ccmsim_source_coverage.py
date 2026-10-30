"""WP1-E6: fictional source subset and restricted-audio gates."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_audit_wp1_e4_ccmsim_metadata import fictional_tables,make_csv
import audit_wp1_e4_ccmsim_metadata as e4
import audit_wp1_e6_ccmsim_source_coverage as e6


class SourceSubsetCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping,cls.pairs=fictional_tables()
        cls.report=e6.coverage(cls.mapping,cls.pairs)

    def test_exact_original_cohort_accounting_and_no_new_audio(self):
        r=self.report
        self.assertEqual(r["annotated_human_pairs"],1130)
        self.assertEqual(r["annotated_audio_clips"],463)
        self.assertEqual(r["mapped_audio_clips"],486)
        self.assertEqual(r["source_corpus_count"],9)
        self.assertEqual(r["single_annotator_pairs"],1052)
        self.assertEqual(sum(r["all_source_pair_counts"].values()),1130)
        self.assertEqual(set(r["source_coverage"]),set(e4.SOURCES))
        for source,info in r["source_coverage"].items():
            self.assertEqual(info["pinned_mapping_clip_count"],54)
            self.assertEqual(info["legal_permission_to_download_redistribute_or_model_audio"],"NOT_DETERMINED")
            self.assertFalse(info["clip_identity_and_20s_segment_parity_verified_with_source_audio"])
        self.assertFalse(r["source_probe_or_audio_download_performed"])
        self.assertFalse(r["same_recording_model_predictions_measured"])
        self.assertFalse(r["general_metric_selected"])

    def test_subsets_account_for_each_edge_and_annotator(self):
        matrix=self.report["all_source_pair_counts"]
        for label,subset in self.report["fixed_upper_bound_subsets"].items():
            included=set(subset["sources"])
            expected=sum(n for k,n in matrix.items()
                         if set(k.split("|")).issubset(included))
            self.assertEqual(expected,subset["pair_upper_bound"])
            self.assertEqual(subset["single_annotator_pairs"]+
                             subset["replicated_annotator_pairs"],expected)
            self.assertEqual(subset["within_source_pairs"]+
                             subset["cross_source_pairs"],expected)
            self.assertFalse(subset["any_actual_audio_or_model_coverage_verified"])
            self.assertFalse(subset["audio_rights_verified"])
        self.assertEqual(
            self.report["fixed_upper_bound_subsets"]["all_nine_source_upper_bound"]["pair_upper_bound"],1130)

    def test_human_label_values_do_not_influence_subset_counts(self):
        rows=e4.read_csv(self.pairs,e4.LABEL_COLUMNS)
        for row in rows:
            for key in e4.LABELS:
                row[key]="0.9"
        altered=e6.coverage(self.mapping,make_csv(e4.LABEL_COLUMNS,rows))
        self.assertEqual(altered,self.report)

    def test_reject_unknown_or_removed_pairs(self):
        rows=e4.read_csv(self.pairs,e4.LABEL_COLUMNS)
        with self.assertRaises(ValueError):
            e6.coverage(self.mapping,make_csv(e4.LABEL_COLUMNS,rows[:-1]))
        with self.assertRaises(ValueError):
            e6.coverage(self.mapping.replace(
                b"survey_audio_id",b"private_audio_path",1), self.pairs)
        changed=[dict(x) for x in rows]
        changed[0]["num_annotators"]="0"
        with self.assertRaises(ValueError):
            e6.coverage(self.mapping,make_csv(e4.LABEL_COLUMNS,changed))

    def test_no_private_clip_id_paths_ratings_or_person_raw_response(self):
        output=json.dumps(self.report,sort_keys=True)
        for forbidden in (
            "survey_audio_id","audio_file_path","fictional-unpublished-track",
            "fake00_00","human_similarity_annotations","participant_response",
        ):
            self.assertNotIn(forbidden,output)
        self.assertTrue(self.report["no_permission_to_fetch_audio_inferred_from_metadata"])
        self.assertFalse(self.report["human_similarity_values_used_for_selection"])
        self.assertFalse(self.report["raw_pair_ids_or_track_paths_or_scores_exported"])


if __name__=="__main__":
    unittest.main()
