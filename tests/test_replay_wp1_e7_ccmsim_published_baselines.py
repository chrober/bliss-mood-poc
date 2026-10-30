"""WP1-E7 frozen third-party scores: all fixtures synthetic, no audio."""
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
import replay_wp1_e7_ccmsim_published_baselines as e7
from test_audit_wp1_e4_ccmsim_metadata import fictional_tables,make_csv


def sample():
    mapping, original = fictional_tables()
    rows=e4.read_csv(original,e4.LABEL_COLUMNS)
    mapped=e4.read_csv(mapping,e4.MAPPING_COLUMNS)
    source={r["survey_audio_id"]:r["dataset"] for r in mapped}
    within=0
    for i,row in enumerate(rows):
        a,b=row["audio_pair"].split("-")
        within+=source[a]==source[b]
        for key in e4.LABELS:
            row[key]=str((i%101)/100.0)
    original=make_csv(e4.LABEL_COLUMNS,rows)
    combined=[]
    targets=("H-Overall","H-Cultural","H-Recommend")
    for i,row in enumerate(rows):
        v=(i%101)/100.0
        rr={"audio_pair":row["audio_pair"]}
        for key in targets:
            rr[key]=str(v)
        for j,key in enumerate(e7.MODEL):
            rr[key]=str(v if j%2==0 else 1.0-v)
        combined.append(rr)
    merged=make_csv(("audio_pair",)+targets+e7.MODEL,combined)
    return mapping,original,merged,(within,1130-within)


class PublishedExternalBaselinesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping,cls.human,cls.combined,cls.source_counts=sample()

    def test_tie_aware_spearman_and_constant_scores(self):
        self.assertAlmostEqual(e7.spearman([1,2,3,4],[4,3,2,1]),-1)
        self.assertAlmostEqual(e7.spearman([1,1,2,3],[1,1,2,3]),1)
        self.assertIsNone(e7.spearman([1,1,1],[1,2,3]))
        with self.assertRaises(ValueError):
            e7.spearman([1,2],[2])

    def test_report_names_and_true_source_strata_only(self):
        r=e7.replay(self.mapping,self.human,self.combined,
                    expected_source_counts=self.source_counts)
        self.assertEqual(r["published_original_human_pair_count"],1130)
        self.assertEqual(r["model_count"],11)
        self.assertEqual(r["human_target_count"],3)
        self.assertFalse(r["global_pairwise_lyrion_general_metric_tested"])
        self.assertFalse(r["source_audio_or_participant_responses_fetched"])
        self.assertFalse(r["musical_metric_winner_selected"])
        self.assertEqual(
            r["source_strata"]["within_source_only"]["pair_count"],
            self.source_counts[0])
        self.assertEqual(
            r["source_strata"]["cross_source_only"]["pair_count"],
            self.source_counts[1])
        s=r["source_strata"]["all_published_pairs"]["human_label_targets"]
        self.assertAlmostEqual(s["H-Overall"]["SP-Melody"],1)
        self.assertAlmostEqual(s["H-Overall"]["SP-Rhythm"],-1)
        self.assertNotIn("fake00_00",json.dumps(r))
        self.assertNotIn("audio_pair",json.dumps(r))
        self.assertNotIn("survey_audio_id",json.dumps(r))

    def test_no_undetected_original_human_score_changes(self):
        row=e4.read_csv(self.combined,("audio_pair",)+e7.HUMAN+e7.MODEL)
        row[0]["H-Overall"]="0.98765"
        with self.assertRaises(ValueError):
            e7.replay(self.mapping,self.human,
                make_csv(("audio_pair",)+e7.HUMAN+e7.MODEL,row),
                expected_source_counts=self.source_counts)

    def test_reject_missing_extra_duplicate_and_invalid_model_scores(self):
        base=e4.read_csv(self.combined,("audio_pair",)+e7.HUMAN+e7.MODEL)
        variants=[]
        variants.append(base[:-1])
        dup=[dict(r) for r in base]
        dup[1]["audio_pair"]=dup[0]["audio_pair"]
        variants.append(dup)
        bad=[dict(r) for r in base]
        bad[0]["SP-Melody"]="nan"
        variants.append(bad)
        bad=[dict(r) for r in base]
        bad[0]["FM-MERT_95"]="1.0000001"
        variants.append(bad)
        for rows in variants:
            with self.subTest(case=len(rows), error=rows[0].get("SP-Melody")), self.assertRaises(ValueError):
                e7.replay(self.mapping,self.human,
                    make_csv(("audio_pair",)+e7.HUMAN+e7.MODEL,rows),
                    expected_source_counts=self.source_counts)

    def test_source_fraction_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            e7.replay(self.mapping,self.human,self.combined)


if __name__=="__main__":
    unittest.main()
