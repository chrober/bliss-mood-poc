"""Synthetic WP3 post-selected sensitivity and redundancy, stdlib only."""
from __future__ import annotations

from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_wp3_snapshot_stability as rob
import build_wp3_research_db as builder
from test_run_local_bliss_essentia_teacher_study import LocalPairedStudyTests, _sha


class WithinCohortStabilityTests(unittest.TestCase):
    def setUp(self):
        fixture = LocalPairedStudyTests("test_real_source_adapters_aggregate_only_no_writes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.root/"wp3-research.sqlite"
        builder.build(fixture.bliss, fixture.essentia, self.db, limit=64)
        with closing(sqlite3.connect(self.db)) as db:
            item=json.loads(db.execute(
                "SELECT value FROM metadata WHERE key='selection_json'"
            ).fetchone()[0])
            for name,names in rob.FOCUS_CLASSES.items():
                catalogue=item["chosen_head_model_ids"][name]["class_labels"]
                catalogue[:len(names)] = names
                self.assertEqual(len(catalogue),len(set(catalogue)))
            db.execute("UPDATE metadata SET value=? WHERE key='selection_json'",
                       (json.dumps(item),))
            db.commit()

    def test_redundancy_and_repeated_sample_sensitivity(self):
        original=(_sha(self.db),_sha(self.fixture.bliss),_sha(self.fixture.essentia))
        result=rob.analyze(self.db,resamples=40)
        self.assertEqual(result["schema"],rob.REPORT_SCHEMA)
        self.assertEqual(result["songs"],64)
        self.assertEqual(result["group_provenance"],"NOT_AVAILABLE")
        self.assertEqual(result["bliss_redundancy"]["all_possible_pairs"],253)
        self.assertEqual(result["bliss_redundancy"]["defined_pairs"]+
                         (253-result["bliss_redundancy"]["defined_pairs"]),253)
        self.assertEqual(len(result["bliss_redundancy"]["focus_pairs"]),10)
        self.assertEqual(len(result["essentia_selected_class_redundancy"]),21)
        self.assertEqual(len(result["selected_cross_model_correlations"]),16)
        self.assertEqual(result["subsampling"]["count"],40)
        self.assertEqual(result["subsampling"]["sample_size"],51)
        for row in result["selected_cross_model_correlations"]:
            self.assertEqual(row["subsamples_valid"],40)
            self.assertGreaterEqual(row["subsample_same_sign_fraction"],0)
            self.assertLessEqual(row["subsample_same_sign_fraction"],1)
            self.assertLessEqual(row["subsample_rho_p10"],row["subsample_rho_median"])
            self.assertLessEqual(row["subsample_rho_median"],row["subsample_rho_p90"])
            self.assertGreaterEqual(row["leave_one_song_out_max_abs_rho_shift"],0)
        self.assertTrue(result["limitations"]["post_selection_same_cohort_winners_curse_possible"])
        serialized=json.dumps(result)
        for private in ("Private Audio","Recording0.flac",
                        str(self.fixture.root),"dddddddddddd"):
            self.assertNotIn(private,serialized)
        self.assertEqual(original,(_sha(self.db),_sha(self.fixture.bliss),_sha(self.fixture.essentia)))

    def test_repeatable_without_independent_validation(self):
        one=rob.analyze(self.db,resamples=25,seed=42)
        two=rob.analyze(self.db,resamples=25,seed=42)
        self.assertEqual(one,two)
        self.assertTrue(one["limitations"][
            "repeated_song_subsampling_not_an_independent_replication"])

    def test_missing_frozen_class_fails_closed(self):
        with closing(sqlite3.connect(self.db)) as db:
            selection=json.loads(db.execute(
                "SELECT value FROM metadata WHERE key='selection_json'"
            ).fetchone()[0])
            selection["chosen_head_model_ids"]["genre"]["class_labels"][0]="no-metal-label"
            db.execute("UPDATE metadata SET value=? WHERE key='selection_json'",
                       (json.dumps(selection),))
            db.commit()
        with self.assertRaisesRegex(ValueError,"Frozen, post-selected class"):
            rob.analyze(self.db,resamples=20)

    def test_no_overwrite_or_song_names_in_report(self):
        existing=self.fixture.root/"stability.json"
        existing.write_text("PRESERVE",encoding="utf-8")
        with patch.object(sys,"argv",["analyze","--research-db",str(self.db),
                                     "--out",str(existing),"--resamples","20"]):
            with self.assertRaises(SystemExit) as cm:
                rob.main()
        self.assertEqual(cm.exception.code,2)
        self.assertEqual(existing.read_text(),"PRESERVE")
        existing.unlink()
        captured=io.StringIO()
        with patch.object(sys,"argv",["analyze","--research-db",str(self.db),
                                     "--out",str(existing),"--resamples","20"]),redirect_stdout(captured):
            self.assertEqual(rob.main(),0)
        public=json.loads(captured.getvalue())
        self.assertEqual(public["songs"],64)
        self.assertEqual(public["selected_posthoc_pairs_checked"],16)
        self.assertNotIn("Private Audio",existing.read_text())
        self.assertNotIn(str(self.fixture.root),existing.read_text())
        self.assertNotIn("Private Audio",captured.getvalue())

    def test_minimum_sample_and_sampling_gates(self):
        with self.assertRaisesRegex(ValueError,"replicate"):
            rob.analyze(self.db,resamples=5)
        with self.assertRaisesRegex(ValueError,"fraction"):
            rob.analyze(self.db,resamples=20,sample_fraction=0.99)


if __name__=="__main__":
    unittest.main()
