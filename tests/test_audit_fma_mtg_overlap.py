"""Offline FMA/MTG metadata provenance; never use TEST song identities."""
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_fma_mtg_overlap as audit


class FmaMtgTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.fma=self.root/"fma_metadata.zip"
        self.mtg=self.root/"raw.meta.tsv"
        self.mtg.write_text(
            "track_id\tartist_name\ttrack_name\n"
            "1\tBJÖRK\tHello\n"
            "2\tArtist X\tA Song\n"
            "3\tArtist Only\tUnrelated\n",
            encoding="utf8")
        self.write_fma()

    def write_fma(self, items=None, missing_fields=False):
        if items is None:
            items=[
                ("101","small","training","Rock","Héllo!","42","Björk"),
                ("102","small","training","Rock","Nonmatch","43","Artist Only"),
                ("103","small","validation","Folk","A Song","50","Artist X"),
                ("104","small","validation","Folk","Untitled","51","Unknown"),
                ("105","small","test","Rock","HIDDEN ANSWER","60","HIDDEN TEST"),
                ("106","medium","test","Classical","Track","70","Not In Study"),
            ]
        s=io.StringIO(newline="")
        w=csv.writer(s)
        w.writerow(["","set","set","track","track","artist","artist"] if not missing_fields
                   else ["","set","set","track","artist","artist"])
        w.writerow(["","subset","split","genre_top","title","id","name"] if not missing_fields
                   else ["","subset","split","genre_top","id","name"])
        w.writerows(items)
        with zipfile.ZipFile(self.fma,"w") as archive:
            archive.writestr("fma_metadata/tracks.csv",s.getvalue())

    def test_exact_artist_title_and_artist_only_candidate_counts(self):
        data=audit.inspect(self.fma,self.mtg)
        self.assertEqual(data["schema"],audit.SCHEMA)
        self.assertEqual(data["coverage"]["training"],2)
        self.assertEqual(data["coverage"]["validation"],2)
        self.assertEqual(data["coverage"]["test_metadata_rows_not_inspected"],1)
        self.assertEqual(data["coverage"]["mtg_catalog_metadata_rows"],3)
        self.assertEqual(data["by_split"]["training"]["possible_exact_artist_title_catalog_matches"],1)
        self.assertEqual(data["by_split"]["training"]["possible_artist_only_catalog_matches"],2)
        self.assertEqual(data["by_split"]["validation"]["possible_exact_artist_title_catalog_matches"],1)
        self.assertEqual(data["by_split"]["validation"]["no_usable_artist_title"],1)
        self.assertEqual(data["by_genre"]["training"]["Rock"]["development_rows"],2)
        self.assertEqual(data["policy"]["fma_official_test"],"untouched_artist_title_genre_metadata_and_audio")
        # The short numeric fake TEST ID may randomly occur as a substring
        # of a legitimate SHA256 digest. Exclude source hashes from this
        # redaction check; validate those hashes separately below.
        exposed=json.dumps({k:v for k,v in data.items() if k!="source_sha256"})
        for sensitive in ("Björk","Hello","Artist X","HIDDEN TEST","HIDDEN ANSWER"):
            self.assertNotIn(sensitive,exposed)
        self.assertNotIn('"105"',exposed)
        self.assertIn("NOT_verified",data["status"])
        self.assertEqual(len(data["source_sha256"]["fma_metadata_archive_sha256"]),64)

    def test_missing_artist_title_header_fails(self):
        self.write_fma(missing_fields=True)
        with self.assertRaisesRegex(ValueError,"missing required"):
            audit.inspect(self.fma,self.mtg)

    def test_duplicate_development_id_fails(self):
        self.write_fma([
            ("101","small","training","Rock","A","42","A"),
            ("101","small","validation","Rock","B","43","B"),
        ])
        with self.assertRaisesRegex(ValueError,"Duplicate FMA"):
            audit.inspect(self.fma,self.mtg)

    def test_test_rows_may_contain_hidden_unparseable_fields(self):
        self.write_fma([
            ("101","small","training","Rock","Song","42","Known"),
            ("102","small","validation","Folk","Song","43","Known 2"),
            ("SECRET TEST ID","small","test","", "", "", ""),
        ])
        data=audit.inspect(self.fma,self.mtg)
        self.assertEqual(data["coverage"]["test_metadata_rows_not_inspected"],1)

    def test_mtg_bad_columns_rejected(self):
        self.mtg.write_text("wrong\tother\nbad\tdata\n",encoding="utf8")
        with self.assertRaisesRegex(ValueError,"artist column"):
            audit.inspect(self.fma,self.mtg)


if __name__=="__main__":
    unittest.main()
