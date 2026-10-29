"""WP2-P3: mock-only exact SHA-pinned existing Rust learner runner.

No user data, no release download, no network and no actual external binary.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_bliss_essentia_join import BLISS_COLUMNS
from prepare_bliss_learner_train_only import prepare, _sha256
from run_verified_bliss_learner import run_verified


def identity_matrix():
    return {"m":{"v":1,"dim":[23,23],
                 "data":[1.0 if i==j else 0.0
                         for i in range(23) for j in range(23)]}}


class LearnerRunnerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.db=self.root/"original-bliss.db"
        self.meta={}
        triples=[]
        rows=[]
        for artist in range(8):
            trio=[]
            for index in range(3):
                key=f"SECRET Artist{artist}/Recording{index}.mp3"
                trio.append(key)
                self.meta[key]={
                    "artist_group":f"artist{artist}",
                    "album_group":f"album{artist}",
                    "recording_group":f"recording{artist}-{index}",
                }
                rows.append((key,*([artist+index/3.0]+[.5]*22)))
            triples.append(trio)
        with closing(sqlite3.connect(self.db)) as conn:
            cols=", ".join(f'"{c}" REAL NOT NULL' for c in BLISS_COLUMNS)
            conn.execute(f'CREATE TABLE TracksV2 ("File" TEXT, {cols})')
            conn.executemany(f'INSERT INTO TracksV2 VALUES ({",".join(["?"]*24)})',rows)
            conn.commit()
        self.original_sha=_sha256(self.db)
        self.stage=self.root/"staged"
        prepare(self.db,triples,self.meta,self.stage)
        self.exe=self.root/"bliss-learner-test-binary"
        self.exe.write_bytes(b"SYNTHETIC_PINNED_LEARNER_NON_EXECUTABLE")
        self.exe_sha=_sha256(self.exe)
        self.output=self.root/"new-learner-result"

    def _mock_run(self, cmd, **kwargs):
        self.assertNotIn("--notifs",cmd)
        self.assertEqual(cmd[cmd.index("--db")+1],
                         str((self.stage/"train-only-bliss.db").resolve()))
        self.assertEqual(cmd[cmd.index("--triplets")+1],
                         str((self.stage/"train-only-triplets.json").resolve()))
        self.assertNotIn(str(self.db.resolve()),cmd)
        self.assertEqual(kwargs["stderr"],-3 if False else __import__("subprocess").DEVNULL)
        output=Path(cmd[cmd.index("--output")+1])
        output.write_text(json.dumps(identity_matrix()),encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def test_staged_verifier_calls_only_train_bundle_and_writes_private_hashes(self):
        with patch("run_verified_bliss_learner.subprocess.run",side_effect=self._mock_run) as proc:
            report=run_verified(self.stage,self.exe,self.exe_sha,self.output)
        self.assertEqual(proc.call_count,1)
        self.assertEqual(report["status"],
                         "TRAIN_ONLY_MATRIX_PRODUCED_NOT_INDEPENDENTLY_VALIDATED")
        self.assertTrue(report["heldout_evaluation_not_run"])
        manifest=json.loads((self.output/"learner-run-manifest-private.json").read_text())
        self.assertEqual(manifest["pinned_executable_sha256"],self.exe_sha)
        self.assertEqual(manifest["output_matrix_sha256"],
                         _sha256(self.output/"learned_matrix.json"))
        self.assertEqual(_sha256(self.db),self.original_sha)
        self.assertNotIn("SECRET",json.dumps(report))
        with self.assertRaises(FileExistsError):
            run_verified(self.stage,self.exe,self.exe_sha,self.output)

    def test_executable_tampering_and_triplet_tampering_block_subprocess(self):
        with patch("run_verified_bliss_learner.subprocess.run") as proc:
            with self.assertRaisesRegex(ValueError,"SHA256"):
                run_verified(self.stage,self.exe,"f"*64,self.output)
            self.assertFalse(proc.called)
            self.assertFalse(self.output.exists())
        v=self.stage/"train-only-triplets.json"
        v.write_text(v.read_text().replace("SECRET","STOLEN"))
        with patch("run_verified_bliss_learner.subprocess.run") as proc:
            with self.assertRaisesRegex(ValueError,"SHA256"):
                run_verified(self.stage,self.exe,self.exe_sha,self.output)
            self.assertFalse(proc.called)

    def test_forged_bundle_with_extra_song_rejected_even_when_rehashed(self):
        db=self.stage/"train-only-bliss.db"
        with closing(sqlite3.connect(db)) as conn:
            conn.execute(f'INSERT INTO TracksV2 VALUES ({",".join(["?"]*24)})',
                         ("EXTRA_ARTIST/hidden.wav",*([0.0]*23)))
            conn.commit()
        manifest_path=self.stage/"train-only-manifest-private.json"
        manifest=json.loads(manifest_path.read_text())
        manifest["train_only_db_sha256"]=_sha256(db)
        manifest_path.write_text(json.dumps(manifest))
        with patch("run_verified_bliss_learner.subprocess.run") as proc:
            with self.assertRaisesRegex(ValueError,"non-training songs"):
                run_verified(self.stage,self.exe,self.exe_sha,self.output)
            self.assertFalse(proc.called)

    def test_corrupt_or_non_psd_output_wont_publish_success(self):
        def invalid_model(cmd,**kwargs):
            p=Path(cmd[cmd.index("--output")+1])
            matrix=identity_matrix()
            matrix["m"]["data"][0]=-1
            p.write_text(json.dumps(matrix),encoding="utf-8")
            return SimpleNamespace(returncode=0)
        with patch("run_verified_bliss_learner.subprocess.run",side_effect=invalid_model):
            with self.assertRaisesRegex(ValueError,"positive semidefinite"):
                run_verified(self.stage,self.exe,self.exe_sha,self.output)
        self.assertFalse((self.output/"learner-run-manifest-private.json").exists())
        self.assertEqual(_sha256(self.db),self.original_sha)

    def test_invalid_timeout_rejected(self):
        with self.assertRaises(ValueError):
            run_verified(self.stage,self.exe,self.exe_sha,self.output,timeout_seconds=1)
        self.assertFalse(self.output.exists())


if __name__=="__main__":
    unittest.main()
