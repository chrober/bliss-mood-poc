"""Synthetic, stdlib-only WP3 feature relationship tests with NO private audio."""
from __future__ import annotations

from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))

import analyze_wp3_snapshot_correlations as a
import build_wp3_research_db as builder
from test_run_local_bliss_essentia_teacher_study import LocalPairedStudyTests, _sha


class DescriptiveWP3Tests(unittest.TestCase):
    def setUp(self):
        fixture = LocalPairedStudyTests("test_real_source_adapters_aggregate_only_no_writes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.root / "wp3-research.sqlite"
        builder.build(fixture.bliss, fixture.essentia, self.db, limit=64)

    def test_correlation_midrank_and_sign(self):
        self.assertAlmostEqual(a._pearson((1,2,3), (3,2,1)), -1)
        self.assertAlmostEqual(a._pearson((1,2,3), (10,20,30)), 1)
        self.assertIsNone(a._pearson((5,5,5), (1,2,3)))
        self.assertEqual(a._midranks((5,1,1,3)), (4,1.5,1.5,3))
        self.assertAlmostEqual(
            a._pearson(a._midranks((1,2,3,4)),a._midranks((4,3,2,1))),-1
        )

    def test_full_matrix_counts_and_only_anonymized_aggregates(self):
        db_original = _sha(self.db)
        inputs = (_sha(self.fixture.bliss), _sha(self.fixture.essentia))
        result = a.describe(self.db, top=6)
        self.assertEqual(result["songs"], 64)
        self.assertEqual(result["status"],
                         "DESCRIPTIVE_COHORT_ONLY_NOT_GROUP_HELDOUT_VALIDATION")
        self.assertEqual(result["group_provenance"], "NOT_AVAILABLE")
        self.assertEqual(result["bliss_dimensions"],23)
        for head,n in (("genre",87),("moodtheme",56)):
            metrics = result["heads"][head]
            self.assertEqual(metrics["total_pairs"],23*n)
            self.assertEqual(metrics["defined_pairs"]+
                             metrics["undefined_constant_or_degenerate_pairs"],23*n)
            self.assertEqual(len(metrics["top_absolute_spearman_pairs_exploratory"]),6)
            for row in metrics["top_absolute_spearman_pairs_exploratory"]:
                self.assertLessEqual(abs(row["pearson_r"]),1)
                self.assertLessEqual(abs(row["spearman_rho"]),1)
                self.assertIn("essentia_class",row)
                self.assertIn("bliss_feature",row)
        payload = json.dumps(result)
        for forbidden in ("Private Audio", str(self.fixture.root),
                          "Recording0.flac", "dddddddddddd"):
            self.assertNotIn(forbidden,payload)
        self.assertTrue(result["limitations"][
            "correlation_is_not_musical_similarity_improvement"])
        self.assertEqual(db_original, _sha(self.db))
        self.assertEqual(inputs,(_sha(self.fixture.bliss),_sha(self.fixture.essentia)))

    def test_stable_and_model_has_no_supervised_group_requirement(self):
        first = a.describe(self.db)
        second = a.describe(self.db)
        self.assertEqual(first,second)
        self.assertTrue(first["limitations"]["no_metric_learning_or_model_fitting_performed"])

    def test_malformed_vector_fails_not_silently_ignored(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("UPDATE paired_tracks SET genre_f32_le=? WHERE track_key=(SELECT track_key FROM paired_tracks LIMIT 1)",
                       (struct.pack("<f",0.2),))
            db.commit()
        with self.assertRaisesRegex(ValueError,"vector size"):
            a.describe(self.db)

    def test_wrong_sqlite_schema_refused(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("PRAGMA user_version=2")
            db.commit()
        with self.assertRaisesRegex(ValueError,"Unrecognized"):
            a.describe(self.db)

    def test_existing_aggregate_not_overwritten(self):
        out = self.fixture.root / "aggregate.json"
        out.write_text("PRESERVE")
        with patch.object(sys,"argv",[
            "describe", "--research-db", str(self.db), "--out", str(out),
        ]):
            with self.assertRaises(SystemExit) as exc:
                a.main()
        self.assertEqual(exc.exception.code,2)
        self.assertEqual(out.read_text(),"PRESERVE")

    def test_cli_new_report_does_not_print_song_identifiers(self):
        out = self.fixture.root / "aggregate.json"
        text = io.StringIO()
        with patch.object(sys,"argv",[
            "describe", "--research-db", str(self.db), "--out",str(out),
        ]),redirect_stdout(text):
            self.assertEqual(a.main(),0)
        self.assertEqual(json.loads(out.read_text())["songs"],64)
        self.assertEqual(json.loads(text.getvalue())["songs"],64)
        self.assertNotIn("Private Audio",text.getvalue())
        self.assertNotIn(str(self.fixture.root),text.getvalue())


if __name__=="__main__":
    unittest.main()
