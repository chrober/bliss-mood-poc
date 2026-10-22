"""Offline FMA validation-only paired 1280D-vs-genre/mood retrieval tests.

All fixtures are synthetic; no FMA/MTG audio, licenses or external models needed.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_fma_genre as fma
import evaluate_fma_embedding_ab as ab


class FMAEmbeddingPairedFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / "features.db"
        self.embeddings = self.root / "embeddings"
        self.embeddings.mkdir()
        self.audio = "e" * 64
        self.encoder_hash = "a" * 64
        self.encoder_model = "discogs-effnet-bsdynamic-1.onnx"
        self.songs = {}
        self.chosen = []
        for genre in range(8):
            for offset in range(2):
                song = f"{genre*2 + offset + 1:06d}"
                self.chosen.append(song)
                self.songs[song] = {
                    "split": "validation", "genre": f"GENRE{genre}",
                    "artist": str(genre*2+offset),
                }
        self.sample_sha = ab.digest_ids(self.chosen)
        self.make_db_and_vectors()

    def make_db_and_vectors(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript("""
                PRAGMA user_version=3;
                CREATE TABLE feature_models (
                    model_key TEXT PRIMARY KEY,
                    embedding_model TEXT NOT NULL,
                    classification_model TEXT NOT NULL,
                    models_sha256_json TEXT NOT NULL,
                    preprocessing_version TEXT NOT NULL,
                    aggregation TEXT NOT NULL,
                    classes_json TEXT NOT NULL,
                    validated_against_essentia INTEGER NOT NULL
                );
                CREATE TABLE feature_tracks (
                    track_file TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    audio_sha256 TEXT NOT NULL,
                    model_key TEXT NOT NULL,
                    scores_f32_le BLOB NOT NULL,
                    patches_analyzed INTEGER NOT NULL,
                    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(track_file, model_id)
                );
            """)
            for head,dims in (("genre",87),("moodtheme",56)):
                conn.execute("INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,?)", (
                    "profile-"+head, self.encoder_model, head+"-head.onnx",
                    json.dumps({self.encoder_model:self.encoder_hash}),
                    ab.PREPROCESSING, fma.ev.AGGREGATION,
                    json.dumps([f"class_{i}" for i in range(dims)]), 0,
                ))
            for song in self.chosen:
                genre=int(self.songs[song]["genre"][5:])
                key=f"FMA/{song}.mp3"
                for head,dims in (("genre",87),("moodtheme",56)):
                    features=[0.01] * dims
                    features[genre]=.8
                    features[(genre+8)%dims]=.25
                    conn.execute(
                        "INSERT INTO feature_tracks(track_file,model_id,capability,"
                        "audio_sha256,model_key,scores_f32_le,patches_analyzed)"
                        "VALUES(?,?,?,?,?,?,?)",
                        (key,head,"genre" if head=="genre" else "mood_theme",
                         self.audio,"profile-"+head,struct.pack("<"+"f"*dims,*features),3),
                    )
                vec=[0.] * 1280
                vec[genre]=1.
                contract=[
                    1,self.encoder_model,self.encoder_hash,ab.PREPROCESSING,
                    "patch_f64_arithmetic_mean_v1","song_f64_l2_then_cast_f32_v1",1280,
                ]
                data={
                    "schema_version":1,"kind":"discogs_effnet_song_embedding",
                    "validation_status":"experimental_unvalidated","dimension":1280,
                    "patches_analyzed":3,"audio_sha256":self.audio,
                    "track_file":key,"encoder_model":self.encoder_model,
                    "encoder_sha256":self.encoder_hash,"preprocessing_version":ab.PREPROCESSING,
                    "pooling_version":"patch_f64_arithmetic_mean_v1",
                    "normalization_version":"song_f64_l2_then_cast_f32_v1",
                    "representation_fingerprint":hashlib.sha256(
                        json.dumps(contract,separators=(",",":"),ensure_ascii=False)
                        .encode()).hexdigest(),"vector_f32":vec,
                }
                (self.embeddings / ab.filename_for_key(key)).write_text(
                    json.dumps(data),encoding="utf-8",
                )
            conn.commit()

    def test_complete_paired_retrieval_on_same_queries_and_candidates(self):
        before=self.db.read_bytes()
        report=ab.evaluate(self.db,self.embeddings,self.chosen,self.songs,self.sample_sha,
                           replicates=120)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertEqual(report["official_split"],"validation")
        self.assertEqual(report["sample_size"],16)
        self.assertEqual(report["distinct_artists"],16)
        self.assertEqual(len(report["methods"]),5)
        self.assertEqual(report["encoder_sha256"],self.encoder_hash)
        self.assertEqual(report["candidate_policy"]["count_per_query"],15)
        self.assertAlmostEqual(report["random_precision_at_5"],1/15)
        for method, stats in report["methods"].items():
            with self.subTest(method=method):
                self.assertEqual(stats["full_queries"],16)
                self.assertEqual(stats["abstained_queries"],0)
                self.assertEqual(stats["query_denominator"],16)
                self.assertEqual(stats["precision_at_5"],.2)
                self.assertEqual(stats["map_at_10"],1.)
                self.assertEqual(stats["ndcg_at_10"],1.)
        for baseline,paired in report["paired_differences"].items():
            for measure in ab.MEASURES:
                self.assertEqual(paired[measure]["embedding_minus_baseline"],0.)
                self.assertEqual(
                    paired[measure]["genre_stratified_shared_query_resampling_95pct_sensitivity"],
                    [0.,0.],
                )
        text=json.dumps(report)
        self.assertNotIn("FMA/000001.mp3",text)
        self.assertNotIn('"artist"',text)

    def test_reject_test_split_or_replaced_sample(self):
        self.songs[self.chosen[0]]["split"]="test"
        with self.assertRaisesRegex(ValueError,"TEST/TRAINING"):
            ab.evaluate(self.db,self.embeddings,self.chosen,self.songs,self.sample_sha,
                        replicates=120)
        self.songs[self.chosen[0]]["split"]="validation"
        with self.assertRaisesRegex(ValueError,"fingerprint changed"):
            ab.evaluate(self.db,self.embeddings,self.chosen,self.songs,"0"*64,
                        replicates=120)

    def test_reject_missing_corrupt_or_foreign_embedding(self):
        file=self.embeddings / ab.filename_for_key(f"FMA/{self.chosen[0]}.mp3")
        original=json.loads(file.read_text())
        for field, bad_value in (("audio_sha256","1"*64),("encoder_sha256","b"*64),
                                 ("patches_analyzed",7),("track_file","FMA/foreign.mp3")):
            corrupt=dict(original)
            corrupt[field]=bad_value
            file.write_text(json.dumps(corrupt))
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"provenance"):
                ab.evaluate(self.db,self.embeddings,self.chosen,self.songs,self.sample_sha,
                            replicates=120)
        file.write_text(json.dumps(original))
        file.unlink()
        with self.assertRaisesRegex(ValueError,"exactly the selected FMA cohort"):
            ab.evaluate(self.db,self.embeddings,self.chosen,self.songs,self.sample_sha,
                        replicates=120)

    def test_query_abstention_counts_as_zero_without_changing_denominator(self):
        vectors={ident:{
            "embedding":tuple(1. if i == int(self.songs[ident]["genre"][5:]) else 0.
                              for i in range(8)),
            "genre":tuple(1. if i == int(self.songs[ident]["genre"][5:]) else 0.
                          for i in range(8)),
            "moodtheme":tuple(1. if i == int(self.songs[ident]["genre"][5:]) else 0.
                              for i in range(8)),
        } for ident in self.chosen}
        vectors[self.chosen[0]]["embedding"]=(0.,)*8
        r=ab.evaluate_paired(vectors,self.chosen,self.songs,seed=1,replicates=120)
        # A shared zero-norm candidate makes all 16 queries incomplete;
        # not merely the query for which the invalid song is the anchor.
        self.assertEqual(r["methods"]["embedding_cosine"]["full_queries"],0)
        self.assertEqual(r["methods"]["embedding_cosine"]["abstained_queries"],16)
        self.assertEqual(r["methods"]["embedding_cosine"]["query_denominator"],16)
        self.assertEqual(r["methods"]["genre_cosine"]["full_queries"],16)

    def test_optional_same_pass_cli_not_enabled_by_default(self):
        # Existing FMA run invokes genre only; opt-in adds both heads and
        # exactly one private embedding file while retaining same track key.
        with tempfile.TemporaryDirectory() as tmp:
            audio=Path(tmp)/"audio.zip"
            with __import__("zipfile").ZipFile(audio,"w") as z:
                z.writestr("000001.mp3", b"synthetic" * 5000)
            def fake_run(cmd, **kwargs):
                if "--embedding-out" in cmd:
                    path=Path(cmd[cmd.index("--embedding-out")+1])
                    path.write_text("{}",encoding="utf-8")
                return SimpleNamespace(returncode=0,stderr="")
            with patch.object(fma.subprocess,"run",side_effect=fake_run) as mock:
                fma.run_inference(Path("/bin/true"),self.root,audio,
                                  {"000001":"000001.mp3"},["000001"],
                                  self.root/"new-genre.db")
                cmd=mock.call_args.args[0]
                self.assertEqual(cmd[cmd.index("--models")+1],"genre")
                self.assertNotIn("--embedding-out",cmd)
                fma.run_inference(Path("/bin/true"),self.root,audio,
                                  {"000001":"000001.mp3"},["000001"],
                                  self.root/"new-both.db",self.root/"private")
                cmd=mock.call_args.args[0]
                self.assertEqual(cmd[cmd.index("--models")+1],"genre,moodtheme")
                self.assertIn("--embedding-out",cmd)
                self.assertIn("FMA/000001.mp3",cmd)
                with self.assertRaises(FileExistsError):
                    fma.run_inference(Path("/bin/true"),self.root,audio,
                                      {"000001":"000001.mp3"},["000001"],
                                      self.root/"unused.db",self.root/"private")


if __name__=="__main__":
    unittest.main()
