"""Synthetic-only checks for the WP3 metadata copy verifier."""
from __future__ import annotations

from contextlib import closing, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_wp3_copied_lyrion_sqlite as verifier
from test_derive_lyrion_research_groups import ResearchLyrionGroupsTests
from test_run_local_bliss_essentia_teacher_study import _sha


class VerifyCopiedLyrionSQLiteTests(unittest.TestCase):
    def setUp(self):
        obj = ResearchLyrionGroupsTests("test_uses_real_snapshot_link_and_lms_album_ids_no_path_guess")
        obj.setUp()
        self.addCleanup(obj.doCleanups)
        self.fixture = obj
        self.library = obj.library
        self.snapshot = obj.snapshot

    def test_read_only_nonidentifying_aggregate(self):
        original = (_sha(self.library), _sha(self.snapshot))
        report = verifier.inspect(self.library, self.snapshot)
        self.assertEqual(report["schema"], "wp3-lyrion-local-copies-validation-v1")
        self.assertEqual(report["library_tracks"], 64)
        self.assertEqual(report["library_albums"], 8)
        self.assertEqual(report["snapshot_tracks"], 64)
        self.assertEqual(report["snapshot_artist_identity_rows"], 65)
        self.assertTrue(report["snapshot_library_mutual_consistency_not_yet_certified"])
        text = json.dumps(report)
        for secret in (str(self.fixture.root), "Private Audio", "artist-mbid", "urlmd5-", "Recording0"):
            self.assertNotIn(secret, text)
        self.assertEqual(original, (_sha(self.library), _sha(self.snapshot)))
        self.assertFalse(Path(str(self.library)+"-wal").exists())

    def test_schema_incompatibility_fails_closed(self):
        with closing(sqlite3.connect(self.snapshot)) as db:
            db.execute("ALTER TABLE track_artist_identity RENAME COLUMN canonical_key TO incorrect_column")
            db.commit()
        with self.assertRaisesRegex(ValueError, "incompatible schema"):
            verifier.inspect(self.library, self.snapshot)

    def test_missing_and_same_file_fail(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            verifier.inspect(self.library, self.library)
        with self.assertRaisesRegex(ValueError, "missing"):
            verifier.inspect(self.library, self.fixture.root / "notfound.sqlite")

    def test_invalid_snapshot_metadata_fails(self):
        with closing(sqlite3.connect(self.snapshot)) as db:
            db.execute("UPDATE metadata SET value='bad' WHERE key='media_roots_identity'")
            db.commit()
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            verifier.inspect(self.library, self.snapshot)

    def test_cli_from_python_file_no_paths_exported(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["verify",
            "--lyrion-library-db", str(self.library),
            "--repeat-identity-db", str(self.snapshot)
        ]), redirect_stdout(out):
            self.assertEqual(verifier.main(), 0)
        self.assertEqual(json.loads(out.getvalue())["library_tracks"], 64)
        self.assertNotIn(str(self.fixture.root), out.getvalue())
        self.assertNotIn("Private Audio", out.getvalue())


if __name__ == "__main__":
    unittest.main()
