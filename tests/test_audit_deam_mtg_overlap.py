"""Offline synthetic checks of conservative DEAM/MTG catalog screening."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_deam_mtg_overlap.py"
spec = importlib.util.spec_from_file_location("audit_deam_mtg_overlap", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DeamMtgAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.deam = self.root / "metadata.zip"
        self.mtg = self.root / "raw.meta.tsv"
        with zipfile.ZipFile(self.deam, "w") as archive:
            archive.writestr(
                "metadata/metadata_2013.csv",
                'song_id,file_name,Artist,Song title\n'
                '1,a.mp3,"Björk","Héllo!"\n'
                '2,b.mp3,Artist X,Foobar\n'
            )
            archive.writestr(
                "metadata/metadata_2014.csv",
                'Id,Artist,Album,Track\n'
                '3,Artist Y,Album,Song 3\n'
                '4,Various Artists,Album,Untitled\n'
            )
            archive.writestr(
                "metadata/metadata_2015.csv",
                'id,Filename,title,artist,album,genre,\n'
                '2001,2001.mp3,A Song,Artist Z,Album,folk,\n'
                '2002,2002.mp3,Another Song,Artist Z,Album,folk,\n'
            )
        self.mtg.write_text(
            "track_id\tartist_name\ttrack_name\n"
            "111\tBJÖRK\tHello\n"
            "222\tArtist Z\tA Song\n"
            "333\tAnother Artist\tAnother Song\n",
            encoding="utf-8",
        )

    def test_no_private_track_values_exported(self):
        report = audit.check(self.deam, self.mtg)
        self.assertEqual(report["schema"], "deam-mtg-exact-metadata-screen-v1")
        self.assertEqual(report["coverage"]["deam_rows_with_valid_artist_title"], 5)
        self.assertEqual(report["coverage"]["mtg_metadata_rows"], 3)
        self.assertEqual(
            report["by_cohort"]["earlier_excerpt"]["mtg_catalog_exact_match_candidates"], 1)
        self.assertEqual(
            report["by_cohort"]["full_song_2015"]["mtg_catalog_exact_match_candidates"], 1)
        self.assertIn("NOT_verified", report["status"])
        output = json.dumps(report)
        for secret in ("Björk", "Artist Z", "2001.mp3", "Héllo!"):
            self.assertNotIn(secret, output)
        self.assertEqual(len(report["source_hashes"]["deam_metadata_zip_sha256"]), 64)

    def test_refuses_unknown_mtg_columns(self):
        self.mtg.write_text("track_id\tguess\n1\ttest\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artist column"):
            audit.check(self.deam, self.mtg)

    def test_conflicting_duplicate_ids_are_excluded(self):
        with zipfile.ZipFile(self.deam, "a") as archive:
            archive.writestr(
                "metadata/extra/metadata_2013.csv",
                "song_id,Artist,Song title\n1,Another,Record\n",
            )
        with self.assertRaisesRegex(ValueError, "Expected DEAM metadata CSVs"):
            audit.check(self.deam, self.mtg)

    def test_key_normalization_is_unicode_aware(self):
        self.assertEqual(audit.clean("  HéLLO --  THE  WORLD!"),
                         "hello the world")
        self.assertEqual(audit.key_name("Song title"), "song_title")


if __name__ == "__main__":
    unittest.main()
