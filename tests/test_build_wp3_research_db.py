"""Synthetic-only integration gates for the private, single-DB WP3 research snapshot."""
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
from test_run_local_bliss_essentia_teacher_study import LocalPairedStudyTests, _sha
from test_derive_lyrion_research_groups import ResearchLyrionGroupsTests

import build_wp3_research_db as builder
import run_local_bliss_essentia_teacher_study as study


class ResearchSnapshotTests(unittest.TestCase):
    def setUp(self):
        source=LocalPairedStudyTests("test_real_source_adapters_aggregate_only_no_writes")
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.source=source
        self.root=source.root
        self.out=self.root/"wp3-research.sqlite"

    def test_preflight_nothing_written_and_aggregation_no_private_keys(self):
        before=(_sha(self.source.bliss),_sha(self.source.essentia))
        summary=builder.build(self.source.bliss,self.source.essentia,None,limit=64)
        self.assertEqual(summary["counts"]["paired_bliss_essentia_tracks"],64)
        self.assertEqual(summary["groups"]["status"],"NOT_AVAILABLE")
        self.assertFalse(summary["private_song_keys_vectors_written_to_local_sqlite"])
        self.assertNotIn("Private Audio",json.dumps(summary))
        self.assertNotIn(str(self.root),json.dumps(summary))
        self.assertFalse(self.out.exists())
        self.assertEqual(before,(_sha(self.source.bliss),_sha(self.source.essentia)))

    def test_single_sqlite_has_exact_bliss23_genre87_mood56_no_invented_groups(self):
        before=(_sha(self.source.bliss),_sha(self.source.essentia))
        summary=builder.build(self.source.bliss,self.source.essentia,self.out,limit=64)
        self.assertTrue(self.out.is_file())
        self.assertEqual(summary["status"],"FEATURE_SNAPSHOT_ONLY_GROUPS_UNVERIFIED")
        with closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM paired_tracks").fetchone()[0],64)
            blobs=db.execute("""
                SELECT bliss_f64_le,genre_f32_le,moodtheme_f32_le,
                       artist_group,album_group,recording_group
                  FROM paired_tracks LIMIT 1
            """).fetchone()
            self.assertEqual([len(x) for x in blobs[:3]],[23*8,87*4,56*4])
            self.assertEqual(blobs[3:],(None,None,None))
            self.assertEqual(db.execute(
                "SELECT value FROM metadata WHERE key='group_readiness'"
            ).fetchone()[0],"NOT_AVAILABLE")
        self.assertEqual(before,(_sha(self.source.bliss),_sha(self.source.essentia)))
        with self.assertRaisesRegex(ValueError,"Group-disjoint research blocked"):
            study.run_research_database(self.out)

    def test_existing_output_is_never_overwritten(self):
        self.out.write_text("DO_NOT_TOUCH")
        with self.assertRaises(FileExistsError):
            builder.build(self.source.bliss,self.source.essentia,self.out,limit=64)
        self.assertEqual(self.out.read_text(),"DO_NOT_TOUCH")

    def test_missing_sources_does_not_create_any_output(self):
        with self.assertRaisesRegex(ValueError,"source databases"):
            builder.build(self.source.bliss,self.root/"unknown-native.sqlite",
                          self.out,limit=64)
        self.assertFalse(self.out.exists())

    def test_missing_half_of_group_pair_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"together"):
            builder.build(self.source.bliss,self.source.essentia,self.out,
                          snapshot=self.root/"snapshot.db",limit=64)
        self.assertFalse(self.out.exists())

    def test_cli_prints_only_aggregate_and_keeps_preflight_no_write(self):
        output=io.StringIO()
        with patch.object(sys,"argv",[
            "builder","--bliss-db",str(self.source.bliss),
            "--feature-db",str(self.source.essentia),"--limit","64"
        ]),redirect_stdout(output):
            self.assertEqual(builder.main(),0)
        json_data=json.loads(output.getvalue())
        self.assertEqual(json_data["counts"]["paired_bliss_essentia_tracks"],64)
        self.assertNotIn("Private Audio",output.getvalue())
        self.assertFalse(self.out.exists())

    def test_real_group_sources_mocked_synthetically_read_study_from_one_db(self):
        real=ResearchLyrionGroupsTests(
            "test_preflight_reports_ready_without_writing_private_groups")
        real.setUp()
        self.addCleanup(real.doCleanups)
        target=real.root/"wp3-research.sqlite"
        original=tuple(_sha(p) for p in (
            real.source.bliss,real.source.essentia,real.snapshot,real.library
        ))
        report=builder.build(
            real.source.bliss,real.source.essentia,target,
            snapshot=real.snapshot,library=real.library,limit=64
        )
        self.assertEqual(report["status"],"READY_FOR_GROUPED_RESEARCH")
        self.assertEqual(report["groups"]["verified_grouped_songs"],64)
        res=study.run_research_database(target)
        self.assertEqual(
            res["coverage"]["counts"]["paired_grouped_songs_accepted"],64)
        self.assertEqual(res["status"],
                         "EXPLORATORY_DEVELOPMENT_NOT_GENERAL_SIMILARITY_VALIDATION")
        self.assertTrue(res["teacher_predictions"]["guarantees"][
            "fit_scaler_ridge_pls_pca_cca_only_on_train"])
        self.assertNotIn("Private Audio",json.dumps(res))
        self.assertNotIn(str(real.root),json.dumps(res))
        self.assertEqual(original,tuple(_sha(p) for p in (
            real.source.bliss,real.source.essentia,real.snapshot,real.library
        )))

    def test_unverified_artist_metadata_must_not_reach_teacher(self):
        real=ResearchLyrionGroupsTests(
            "test_preflight_reports_ready_without_writing_private_groups")
        real.setUp()
        self.addCleanup(real.doCleanups)
        with closing(sqlite3.connect(real.snapshot)) as db:
            db.execute("DELETE FROM track_artist_identity WHERE database_file=?",
                       (next(iter(real.source.all_groups)),))
            db.commit()
        target=real.root/"wp3-research.sqlite"
        report=builder.build(
            real.source.bliss,real.source.essentia,target,
            snapshot=real.snapshot,library=real.library,limit=64
        )
        self.assertEqual(report["status"],"FEATURE_SNAPSHOT_ONLY_GROUPS_UNVERIFIED")
        self.assertEqual(report["groups"]["status"],"BLOCKED")
        with self.assertRaisesRegex(ValueError,"Group-disjoint research blocked"):
            study.run_research_database(target)


if __name__=="__main__":
    unittest.main()
