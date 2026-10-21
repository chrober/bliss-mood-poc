"""Synthetic offline tests for bounded 80-song FMA cache; no original audio."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import fma_selected_audio_cache as fc


class FMASparseCacheTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.meta=self.root/"fma-metadata.zip"
        self.audio=self.root/"fma-small.zip"
        self.bundle=self.root/"cache"/"selected.zip"
        self.manifest=self.root/"cache"/"selection.json"
        buffer=io.StringIO(newline="")
        writer=csv.writer(buffer)
        writer.writerow(["","set","set","track","artist"])
        writer.writerow(["","subset","split","genre_top","id"])
        names=("Rock","Pop","Electronic","Hip-Hop","Experimental",
               "Instrumental","International","Folk")
        with zipfile.ZipFile(self.audio,"w") as z:
            for j,name in enumerate(names):
                for k in range(2):
                    id=f"{j*10+k+100:06d}"
                    writer.writerow([id,"small","validation",name,id])
                    z.writestr(f"fma_small/{id[:3]}/{id}.mp3",bytes([j+20,k+10])*8200)
            # TEST ID with invalid metadata/track reference intentionally not used:
            writer.writerow(["INVALID","small","test","",""])
        with zipfile.ZipFile(self.meta,"w") as z:
            z.writestr("fma_metadata/tracks.csv",buffer.getvalue())

    def create(self):
        return fc.pack(self.audio,self.meta,None,screened=False,
                       bundle=self.bundle,manifest_path=self.manifest,
                       per_genre=2,seed=20261021,enforce_publisher_shas=False)

    def check(self):
        return fc.verify(self.bundle,self.manifest,metadata=self.meta,mtg=None,
                         screened=False,per_genre=2,seed=20261021,
                         enforce_publisher_shas=False)

    def test_pack_and_verify_reuse_exact_16_songs_and_origins(self):
        d=self.create()
        self.assertEqual(len(d["chosen"]),16)
        self.assertEqual(fc.sample_digest(d["chosen"]),d["sample_id_sha256"])
        self.assertEqual(d["publisher_audio_zip_sha256"],fc.fma.sha256_file(self.audio))
        self.assertEqual(self.check(),d)
        with zipfile.ZipFile(self.bundle) as z:
            self.assertEqual(len(z.namelist()),16)
            self.assertTrue(all(x.startswith("selected/") for x in z.namelist()))
        with self.assertRaises(FileExistsError):
            self.create()
        self.audio.unlink()
        self.assertEqual(self.check(),d) # warm restore no original full ZIP needed

    def test_reject_corrupt_member_or_changed_manifest(self):
        self.create()
        self.bundle.write_bytes(self.bundle.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"ZIP SHA"):
            self.check()
        # Protect against a coordinated rewrite of only the outer ZIP checksum.
        d=json.loads(self.manifest.read_text())
        d["bundle_zip_sha256"]=fc.fma.sha256_file(self.bundle)
        self.manifest.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"ZIP"):
            self.check()

    def test_reject_changed_metadata_or_reordered_selection(self):
        self.create()
        d=json.loads(self.manifest.read_text())
        d["chosen"]=list(reversed(d["chosen"]))
        self.manifest.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            self.check()
        d["chosen"]=list(reversed(d["chosen"]))
        self.manifest.write_text(json.dumps(d))
        with zipfile.ZipFile(self.meta,"a") as z:
            z.writestr("unrelated.txt",b"changed")
        with self.assertRaisesRegex(ValueError,"metadata archive SHA"):
            self.check()


if __name__=="__main__":
    unittest.main()
