"""Synthetic WP2-P2 train-only staging, no original Bliss writes or personal labels."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_bliss_essentia_join import BLISS_COLUMNS
from prepare_bliss_learner_train_only import prepare, _sha256


class TrainOnlyStagingTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=self.root/"bliss.db"
        self.trips=[]
        self.metadata={}
        all_rows=[]
        for artist in range(8):
            trio=[]
            for member in range(3):
                key=f"Private Artist {artist}/Secret Song {member}.flac"
                trio.append(key)
                self.metadata[key]={
                    "artist_group":f"opaque-artist-{artist}",
                    "album_group":f"opaque-album-{artist}",
                    "recording_group":f"opaque-recording-{artist}-{member}",
                }
                all_rows.append((key,*([artist+member*.5]+[.5]*22)))
            self.trips.append(trio)
        cols=", ".join('"'+c+'" REAL NOT NULL' for c in BLISS_COLUMNS)
        with sqlite3.connect(self.db) as conn:
            conn.execute(f'CREATE TABLE TracksV2 ("File" TEXT PRIMARY KEY, {cols})')
            conn.executemany(
                f'INSERT INTO TracksV2 VALUES ({",".join("?" for _ in range(24))})',all_rows
            )
            conn.commit()

    def test_stages_only_train_songs_and_original_hash_unchanged(self):
        before=_sha256(self.db)
        result=prepare(self.db,self.trips,self.metadata,self.root/"staged")
        self.assertEqual(_sha256(self.db),before)
        self.assertEqual(result["status"],"PRIVATE_STAGING_CREATED__NO_TRAINING_EXECUTED")
        self.assertEqual(result["train_holdout_song_overlap"],0)
        self.assertEqual(result["train_triplets"]+result["holdout_triplets"],8)
        self.assertGreaterEqual(result["train_triplets"],5)
        newdir=self.root/"staged"
        train=json.loads((newdir/"train-only-triplets.json").read_text())
        with sqlite3.connect(newdir/"train-only-bliss.db") as db:
            columns=[a[1] for a in db.execute("PRAGMA table_info(TracksV2)").fetchall()]
            self.assertEqual(columns,["File",*BLISS_COLUMNS])
            keys={a[0] for a in db.execute("SELECT File FROM TracksV2")}
            self.assertEqual(keys,{key for trio in train for key in trio})
            self.assertLess(len(keys),len(self.metadata))
            for triple in train:
                self.assertTrue(set(triple)<=keys)
        manifest=json.loads((newdir/"train-only-manifest-private.json").read_text())
        self.assertEqual(manifest["train_triplets_sha256"],_sha256(newdir/"train-only-triplets.json"))
        self.assertEqual(manifest["train_only_db_sha256"],_sha256(newdir/"train-only-bliss.db"))
        self.assertEqual(manifest["status"],"NOT_TRAINED__TRAIN_ONLY_STAGING")
        self.assertTrue(manifest["upstream_learner_final_matrix_trained_only_on_staged_train_subset"])
        rendered=json.dumps(result)
        self.assertNotIn("Private Artist",rendered)
        self.assertNotIn(str(self.root),rendered)
        with self.assertRaises(FileExistsError):
            prepare(self.db,self.trips,self.metadata,newdir)
        self.assertEqual(before,_sha256(self.db))

    def test_missing_bliss_feature_causes_fail_before_output_creation(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE TracksV2 SET Tempo=NULL")
            conn.commit()
        with self.assertRaisesRegex(ValueError,"lacks unique"):
            prepare(self.db,self.trips,self.metadata,self.root/"none")
        self.assertFalse((self.root/"none").exists())

    def test_missing_groups_and_entangled_survey_fail_before_any_staging(self):
        groups=dict(self.metadata)
        groups.pop(self.trips[2][0])
        with self.assertRaises(ValueError):
            prepare(self.db,self.trips,groups,self.root/"missing-groups")
        self.assertFalse((self.root/"missing-groups").exists())
        groups={k:dict(v,artist_group="same-artist") for k,v in self.metadata.items()}
        with self.assertRaisesRegex(ValueError,"No independent"):
            prepare(self.db,self.trips,groups,self.root/"entangled")
        self.assertFalse((self.root/"entangled").exists())

    def test_learner_minimum_five_training_votes_is_enforced(self):
        with self.assertRaisesRegex(ValueError,"at least 5"):
            prepare(self.db,self.trips[:3],
                    {k:self.metadata[k] for trio in self.trips[:3] for k in trio},
                    self.root/"too-few")
        self.assertFalse((self.root/"too-few").exists())

    def test_db_is_not_implicitly_created(self):
        missing=self.root/"not-a-database.db"
        with self.assertRaises(ValueError):
            prepare(missing,self.trips,self.metadata,self.root/"missing-source")
        self.assertFalse(missing.exists())
        self.assertFalse((self.root/"missing-source").exists())


if __name__=="__main__":
    unittest.main()
