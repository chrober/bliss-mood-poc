"""WP3-R3 synthetic end-to-end local, read-only grouped Bliss/Essentia study."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import run_local_bliss_essentia_teacher_study as study
from audit_bliss_essentia_join import BLISS_COLUMNS
import evaluate_similarity as ev


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalPairedStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.root=root
        self.bliss=root/"bliss.db"
        self.essentia=root/"features.db"
        self.groups=root/"private-groups.json"
        self.out=root/"private-aggregate.json"
        fields=", ".join(f'"{x}" REAL' for x in BLISS_COLUMNS)
        with closing(sqlite3.connect(self.bliss)) as db:
            db.execute(f'CREATE TABLE TracksV2 ("File" TEXT, {fields})')
            for i in range(64):
                x0=.1+.7*i/65
                x1=.5+.4*math.sin(i*.2)
                x2=.5+.4*math.cos(i*.37)
                values=[x0,x1,x2]+[.05+.03*((i+j*7)%21) for j in range(20)]
                key=f"Private Audio/Artist{i//8}/Recording{i}.flac"
                db.execute(f'INSERT INTO TracksV2 VALUES ({",".join(["?"]*24)})',
                           (key,*values))
            db.commit()
        with closing(sqlite3.connect(self.essentia)) as db:
            db.executescript("""
                PRAGMA user_version=3;
                CREATE TABLE feature_models(
                    model_key TEXT PRIMARY KEY,embedding_model TEXT,
                    classification_model TEXT, models_sha256_json TEXT,
                    preprocessing_version TEXT, aggregation TEXT,
                    classes_json TEXT, validated_against_essentia INTEGER
                );
                CREATE TABLE feature_tracks(
                    track_file TEXT, model_id TEXT, capability TEXT,
                    model_key TEXT, audio_sha256 TEXT, scores_f32_le BLOB,
                    patches_analyzed INTEGER, PRIMARY KEY(track_file,model_id)
                );
            """)
            for head,(cap,dims) in ev.MODELS.items():
                classifier=head+".onnx"
                db.execute("INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,?)",
                    (head,"discogs-effnet.onnx",classifier,
                     json.dumps({"discogs-effnet.onnx":"b"*64,classifier:"c"*64}),
                     "experimental-essentia-cpp-dsp-v1-unvalidated",
                     ev.AGGREGATION,
                     json.dumps([f"head-{head}-{i}" for i in range(dims)]),0))
                for i in range(64):
                    x0=.1+.7*i/65
                    x1=.5+.4*math.sin(i*.2)
                    x2=.5+.4*math.cos(i*.37)
                    values=[.13+.55*x0,.1+.6*x1,.1+.6*x2]+[
                        .15+.008*((i*5+j*7)%49) for j in range(dims-3)
                    ]
                    key=f"Private Audio/Artist{i//8}/Recording{i}.flac"
                    db.execute("INSERT INTO feature_tracks VALUES(?,?,?,?,?,?,?)",
                        (key,head,cap,head,"d"*64,struct.pack("<"+"f"*dims,*values),17))
            db.commit()
        self.all_groups={
            f"Private Audio/Artist{i//8}/Recording{i}.flac":{
                "artist_group":f"Secret Artist {i//8}",
                "album_group":f"Secret Album {i//8}",
                "recording_group":f"Secret Recording {i}"
            }
            for i in range(64)
        }
        self.groups.write_text(json.dumps(self.all_groups),encoding="utf-8")

    def test_real_source_adapters_aggregate_only_no_writes(self):
        original=(_sha(self.bliss),_sha(self.essentia),_sha(self.groups))
        res=study.run_study(self.bliss,self.essentia,self.groups,limit=64)
        self.assertEqual(res["coverage"]["counts"]["paired_grouped_songs_accepted"],64)
        self.assertEqual(res["correlations"]["train_song_count"]+
                         res["correlations"]["holdout_song_count"],64)
        self.assertTrue(res["teacher_predictions"]["guarantees"][
            "fit_scaler_ridge_pls_pca_cca_only_on_train"])
        self.assertEqual(res["bliss_only_geometry_proxy"][
            "input_at_student_inference"],"Bliss_23D_only")
        self.assertEqual(original,(_sha(self.bliss),_sha(self.essentia),_sha(self.groups)))
        self.assertEqual(res,study.run_study(self.bliss,self.essentia,self.groups,limit=64))
        rendered=json.dumps(res)
        for forbidden in ("Private Audio","Secret Artist","Secret Album",
                          "Recording0.flac",str(self.root),"dddddddddddddddd"):
            self.assertNotIn(forbidden,rendered)

    def test_missing_metadata_never_falls_back_to_path_artist_guess(self):
        altered=dict(self.all_groups)
        altered.pop(next(iter(altered)))
        self.groups.write_text(json.dumps(altered),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"incomplete group provenance"):
            study.run_study(self.bliss,self.essentia,self.groups,limit=64)

    def test_unsafe_output_existing_is_untouched(self):
        self.out.write_text("NEVER_REPLACE",encoding="utf-8")
        with patch.object(sys,"argv",[
            "research","--bliss-db",str(self.bliss),
            "--feature-db",str(self.essentia),
            "--group-metadata-json",str(self.groups),
            "--limit","64","--out",str(self.out),
        ]):
            with self.assertRaises(SystemExit) as cm:
                study.main()
        self.assertEqual(cm.exception.code,2)
        self.assertEqual(self.out.read_text(),"NEVER_REPLACE")

    def test_local_cli_writes_only_aggregate(self):
        with patch.object(sys,"argv",[
            "research","--bliss-db",str(self.bliss),
            "--feature-db",str(self.essentia),
            "--group-metadata-json",str(self.groups),
            "--limit","64","--out",str(self.out),
        ]):
            self.assertEqual(study.main(),0)
        obj=json.loads(self.out.read_text())
        self.assertEqual(obj["coverage"]["counts"]["paired_grouped_songs_accepted"],64)
        self.assertNotIn("Private Audio",self.out.read_text())
        self.assertFalse((self.root/"bliss.db-wal").exists())
        self.assertFalse((self.root/"features.db-wal").exists())

if __name__=="__main__":
    unittest.main()
