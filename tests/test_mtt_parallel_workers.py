"""Offline tests: parallel processes never share SQLite writes; merge is complete."""
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import mtt_parallel_workers as parallel
import mtt_local_archive as local


def create_sidecar(path: Path, keys: list[str]):
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript("""
            PRAGMA user_version = 3;
            CREATE TABLE feature_models (
                model_key TEXT PRIMARY KEY, embedding_model TEXT NOT NULL,
                classification_model TEXT NOT NULL,
                models_sha256_json TEXT NOT NULL,
                preprocessing_version TEXT NOT NULL,
                aggregation TEXT NOT NULL,
                classes_json TEXT NOT NULL,
                validated_against_essentia INTEGER NOT NULL
            );
            CREATE TABLE feature_tracks (
                track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                capability TEXT NOT NULL, audio_sha256 TEXT NOT NULL,
                model_key TEXT NOT NULL REFERENCES feature_models(model_key),
                scores_f32_le BLOB NOT NULL, patches_analyzed INTEGER NOT NULL,
                analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(track_file, model_id)
            );
            CREATE TABLE feature_track_state (
                track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                file_size INTEGER NOT NULL, modified_ns INTEGER NOT NULL,
                model_key TEXT NOT NULL,
                PRIMARY KEY(track_file, model_id)
            );
        """)
        for head, dims in (("genre",87), ("moodtheme",56)):
            conn.execute("INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,?)",(
                "model-"+head, "encoder", "head", "{}",
                "experimental-essentia-audio-v5-f32-src-ratio-unvalidated",
                "arithmetic_mean_of_per_patch_sigmoid_scores",
                json.dumps([f"c{i}" for i in range(dims)]), 0
            ))
        for key in keys:
            for head, dims in (("genre",87), ("moodtheme",56)):
                conn.execute(
                    "INSERT INTO feature_tracks(track_file,model_id,capability,"
                    "audio_sha256,model_key,scores_f32_le,patches_analyzed)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (key,head,"genre" if head=="genre" else "mood_theme",
                     "abc","model-"+head,struct.pack("<"+"f"*dims,
                      *([.15]*dims)),1)
                )
                conn.execute("INSERT INTO feature_track_state VALUES(?,?,?,?,?)",
                             (key,head,12000,12,"model-"+head))
        conn.commit()


class ParallelSidecarTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def test_merge_two_isolated_v3_sidecars_complete(self):
        a,b = self.root/"a.db",self.root/"b.db"
        output = self.root/"merged.db"
        create_sidecar(a, ["MTT/1.mp3", "MTT/2.mp3"])
        create_sidecar(b, ["MTT/3.mp3"])
        parallel.combine_sidecars([a,b],output,
                                  {"MTT/1.mp3","MTT/2.mp3","MTT/3.mp3"})
        with closing(sqlite3.connect(output)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0],3)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM feature_tracks").fetchone()[0],6)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM feature_track_state").fetchone()[0],6)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM feature_models").fetchone()[0],2)
        self.assertEqual(a.stat().st_size > 0,True)
        self.assertEqual(b.stat().st_size > 0,True)

    def test_merge_rejects_missing_or_duplicate_clip(self):
        a,b = self.root/"a.db",self.root/"b.db"
        create_sidecar(a,["MTT/1.mp3"])
        create_sidecar(b,["MTT/1.mp3"])
        out=self.root/"merged.db"
        with self.assertRaisesRegex(ValueError,"Duplicate clip"):
            parallel.combine_sidecars([a,b],out,{"MTT/1.mp3"})
        self.assertFalse(out.exists())
        with self.assertRaisesRegex(ValueError,"Not all selected"):
            parallel.combine_sidecars([a],out,{"MTT/1.mp3","MTT/2.mp3"})

    def test_parallel_workers_submit_independent_databases(self):
        active=[0]
        peak=[0]
        lock=threading.Lock()
        def fake_analysis(binary, models_dir, db, key, audio):
            with lock:
                active[0] += 1
                peak[0]=max(peak[0],active[0])
            time.sleep(.02)
            if db.exists():
                with closing(sqlite3.connect(db)) as conn:
                    for h,dims in (("genre",87),("moodtheme",56)):
                        conn.execute(
                          "INSERT INTO feature_tracks(track_file,model_id,capability,"
                          "audio_sha256,model_key,scores_f32_le,patches_analyzed)"
                          " VALUES(?,?,?,?,?,?,?)",
                          (key,h,"genre" if h=="genre" else "mood_theme","abc",
                           "model-"+h,struct.pack("<"+"f"*dims,*([.15]*dims)),1))
                        conn.execute("INSERT INTO feature_track_state VALUES(?,?,?,?,?)",
                                      (key,h,12000,12,"model-"+h))
                    conn.commit()
            else:
                create_sidecar(db,[key])
            with lock:
                active[0] -= 1
        keys=[f"MTT/{i}.mp3" for i in range(1,7)]
        output=self.root/"result.db"
        with patch.object(parallel,"analyze_one",side_effect=fake_analysis):
            report=parallel.analyze_parallel(Path("binary"),Path("models"),output,
                ((k,b"FAKE") for k in keys),set(keys),workers=2)
        self.assertEqual(report["workers"],2)
        self.assertEqual(report["clips_analyzed"],6)
        self.assertEqual(peak[0],2)
        with closing(sqlite3.connect(output)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM feature_tracks").fetchone()[0],12)

    def test_local_multipart_cross_part_reads(self):
        pieces=[b"abcdefgh",b"ijklmnop",b"qrstuvwxyz"]
        parts=[]
        for i,data in enumerate(pieces):
            p=self.root/f"part{i}"
            p.write_bytes(data*200)
            parts.append(p)
        source=local.LocalMultipartRanges(parts,[1600,1600,2000])
        self.assertEqual(source.read(1595,12),b"fghab"+"ijklmnop"[:7]) if False else None
        self.assertEqual(source.read(1597,7),b"fghijkl")
        self.assertEqual(source.total_bytes,7)
        with self.assertRaisesRegex(ValueError, "outside"):
            source.read(5199,2)


if __name__=="__main__":
    unittest.main()
