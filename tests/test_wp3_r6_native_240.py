"""All synthetic: freeze 240 exact keys and verify native C++ 87/56/2 + 1280D contracts."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_prepare_wp3_blinded_bliss_student_pilot import BlindStudentPilotTests
import wp3_r6_native_240 as r6
import evaluate_wp3_r6_240 as evaluation


def _hash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class FakeArgs:
    pass


class NativeR6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        o=BlindStudentPilotTests("test_deterministic_and_frozen_model")
        o.setUp()
        cls.obj=o
        cls.root=o.src.root
        cls.audio=cls.root/"source-audio"
        cls.audio.mkdir()
        cls.models=cls.root/"models"
        cls.models.mkdir()
        cls.tools=cls.root/"tools"
        cls.tools.mkdir()
        cls.scanner=cls.tools/"bliss-mood.exe"
        cls.scanner.write_bytes(b"fixture-scanner")
        (cls.tools/"BUILD.txt").write_text("da8fecee23930c2e52abcb473a62b8178b2d5474")
        (cls.tools/"SHA256SUMS.txt").write_text(_hash(cls.scanner)+"  bliss-mood.exe")
        cls.worker_dir=cls.root/"worker"
        cls.worker_dir.mkdir()
        cls.worker=cls.worker_dir/"bliss-essentia-worker.exe"
        cls.worker.write_bytes(b"fixture-native")
        (cls.worker_dir/"worker-dependencies.json").write_text(json.dumps({
            "schema_version":1,"files":{
                cls.worker.name:{"sha256":_hash(cls.worker),"size_bytes":cls.worker.stat().st_size}}
        }))
        for filename in r6.MODELS.values():
            (cls.models/filename).write_bytes(("synthetic-"+filename).encode())
        for head,filename in r6.LABELS.items():
            (cls.models/filename).write_text(json.dumps({
                "classes":["synthetic-"+head+"-"+str(i) for i in range(r6.DIMS[head])]
            }))
        cls.keys=[item["track_file"] for item in json.loads(
            o.manifest_path.read_text())["selected_songs"]]
        for key in cls.keys:
            p=cls.audio.joinpath(*key.split("/"))
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(("fake audio identity "+key).encode())
        cls.args=FakeArgs()
        a=cls.args
        a.bliss_db=o.src.source.bliss
        a.snapshot=o.src.snapshot
        a.library=o.src.library
        a.old_grouped_db=o.obj.old
        a.old_native_db=o.obj.old
        a.r5_manifest=o.manifest_path
        a.source_root=cls.audio
        a.models_dir=cls.models
        a.scanner=cls.scanner
        a.worker=cls.worker
        a.out_dir=cls.root/"new-r6"
        a.plan_dir=None
        cls.fake_model_hashes={
            name:_hash(cls.models/name) for name in
            (*r6.MODELS.values(),*r6.LABELS.values())}
        with patch.object(r6,"EXPECTED_EXE_SHA",_hash(cls.scanner)), \
             patch.object(r6,"_model_evidence",
                          return_value=cls.fake_model_hashes):
            cls.prepared=r6.prepare(a)
        cls.db_absent_after_prepare=not (cls.root/"new-r6"/"native-features.sqlite").exists()
        cls.plan=_load(cls.root/"new-r6"/"private-scan-plan.json")
        a.plan_dir=a.out_dir
        a.out_dir=None

    @classmethod
    def tearDownClass(cls):
        cls.obj.doCleanups()

    def test_preflight_locked_240_and_manifest_private(self):
        self.assertEqual(self.prepared["songs"],240)
        self.assertEqual(self.prepared["status"],"READY_FOR_FROZEN_NATIVE_CPP_SCAN")
        data=(self.args.plan_dir/"exact-240-tracks.txt").read_text()
        self.assertEqual(len(data.splitlines()),240)
        self.assertEqual(len(set(data.splitlines())),240)
        self.assertTrue((self.args.plan_dir/"embeddings").is_dir())
        self.assertTrue(self.db_absent_after_prepare)
        self.assertNotIn("Private New Validation",str(self.prepared))

    def test_source_hash_guard_fails_closed(self):
        key=self.keys[0]
        path=self.audio.joinpath(*key.split("/"))
        original=path.read_bytes()
        try:
            path.write_bytes(b"mutated")
            with self.assertRaisesRegex(ValueError,"Audio bytes changed"):
                r6.verify(self.args,require_outputs=False)
        finally:
            path.write_bytes(original)
        status=r6.verify(self.args,require_outputs=False)
        self.assertEqual(status["source_audio_sha256_checked"],240)

    def test_manifest_tampering_detected(self):
        path=self.args.plan_dir/"exact-240-tracks.txt"
        original=path.read_bytes()
        try:
            path.write_bytes(b"tamper\n")
            with self.assertRaisesRegex(ValueError,"Output manifest not frozen"):
                r6.verify(self.args,require_outputs=False)
        finally:
            path.write_bytes(original)

    def test_unsafe_track_input_rejected(self):
        for key in ("../x.flac","/absolute.wav","C:/escape.mp3",
                    "sub\\path.flac","sub/./file","sub/../file","sub//file",
                    "sub\nline"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    r6._safe_track(key,self.audio)

    def test_complete_240_real_shape_synthetic_native_outputs(self):
        dest=self.args.plan_dir
        dbpath=dest/"native-features.sqlite"
        with closing(sqlite3.connect(dbpath)) as db:
            db.execute("PRAGMA user_version=3")
            db.execute("""CREATE TABLE feature_models (
               model_key TEXT PRIMARY KEY, preprocessing_version TEXT,
               embedding_model TEXT, classification_model TEXT,
               models_sha256_json TEXT, classes_json TEXT)""")
            db.execute("""CREATE TABLE feature_tracks(
               track_file TEXT, model_id TEXT, model_key TEXT,
               audio_sha256 TEXT, patches_analyzed INTEGER,
               scores_f32_le BLOB)""")
            for head in r6.DIMS:
                model_hash={
                    r6.MODELS["encoder"]:self.fake_model_hashes[r6.MODELS["encoder"]],
                    r6.MODELS[head]:self.fake_model_hashes[r6.MODELS[head]],
                    "essentia_cpp_worker_binary_sha256":_hash(self.worker)}
                cls=_load(self.models/r6.LABELS[head])["classes"]
                db.execute("INSERT INTO feature_models VALUES (?,?,?,?,?,?)",
                    (head,"experimental-essentia-cpp-dsp-v1-unvalidated",
                     r6.MODELS["encoder"],r6.MODELS[head],
                     json.dumps(model_hash),json.dumps(cls)))
            for key in self.keys:
                for head,dim in r6.DIMS.items():
                    values = ([0.5,0.5] if head=="voice" else
                              [0.05+0.65*(i/max(1,dim-1)) for i in range(dim)])
                    scores=struct.pack("<"+"f"*dim,*values)
                    db.execute("INSERT INTO feature_tracks VALUES (?,?,?,?,?,?)",
                         (key,head,head,self.plan["private_source_audio_sha256_by_key"][key],
                          1,scores))
            db.commit()
        fp=hashlib.sha256(json.dumps([
            1,r6.MODELS["encoder"],
            self.fake_model_hashes[r6.MODELS["encoder"]],
            "experimental-essentia-cpp-dsp-v1-unvalidated",
            r6.EMBED_POOL,r6.EMBED_NORM,1280
        ],separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        for key in self.keys:
            doc={
                "schema_version":1,"kind":"discogs_effnet_song_embedding",
                "validation_status":"experimental_unvalidated",
                "dimension":1280,"track_file":key,
                "audio_sha256":self.plan["private_source_audio_sha256_by_key"][key],
                "patches_analyzed":1,"encoder_model":r6.MODELS["encoder"],
                "encoder_sha256":self.fake_model_hashes[r6.MODELS["encoder"]],
                "preprocessing_version":"experimental-essentia-cpp-dsp-v1-unvalidated",
                "pooling_version":r6.EMBED_POOL,"normalization_version":r6.EMBED_NORM,
                "representation_fingerprint":fp,
                "vector_f32":[1.0]+[0.0]*1279
            }
            file=dest/"embeddings"/(hashlib.sha256(key.encode()).hexdigest()+".json")
            file.write_text(json.dumps(doc))
        result=r6.verify(self.args)
        self.assertEqual(result["exact_new_songs"],240)
        self.assertEqual(result["complete_pooled_embedding1280"],240)
        self.assertFalse(result["human_perceptual_similarity_quality_measured"])
        self.assertNotIn("Private New Validation",json.dumps(result))
        first=dest/"embeddings"/(hashlib.sha256(self.keys[0].encode()).hexdigest()+".json")
        old=first.read_bytes()
        try:
            data=_load(first)
            data["encoder_sha256"]="0"*64
            first.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"embedding provenance mismatch"):
                r6.verify(self.args)
        finally:
            first.write_bytes(old)

    def test_evaluator_distance_fixed_pair_contract(self):
        # 240 fake singers with a nonzero 23D range; no sklearn fitting here.
        import numpy as np
        x=np.asarray([[float(i),float(i%7)] for i in range(240)])
        self.assertEqual(len(evaluation._distance(np,x)),28680)
        self.assertEqual(len(evaluation._cosine_dissimilarities(
            np,x+1.0)),28680)


def _load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
