"""Synthetic-only end-to-end numerical gate for frozen WP3-R6 100->240 protocol."""
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
import evaluate_wp3_r6_240 as r6
from research_bliss_essentia_teacher_models import _requires_sklearn


def _sha(p:Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class FrozenTeacherProtocolTests(unittest.TestCase):
    def setUp(self):
        self.context=tempfile.TemporaryDirectory(prefix="synthetic-wp3-r6-")
        self.addCleanup(self.context.cleanup)
        self.root=Path(self.context.name)
        self.bliss=self.root/"dummy-bliss.db"
        self.bliss.write_bytes(b"fictional source sentinel, no real Bliss used")
        self.old=self.root/"old.sqlite"
        self.manifest=self.root/"new.json"
        self.protocol=self.root/"protocol.json"
        self.plan=self.root/"plan"
        self.plan.mkdir()
        self.keys=[f"Fictional New Artist {i:03d}/track.flac" for i in range(240)]
        self.manifest.write_text(json.dumps({"selected_songs":[
            {"track_file":k} for k in self.keys]}))
        self.development=[]
        with closing(sqlite3.connect(self.old)) as con:
            con.execute("CREATE TABLE paired_tracks(track_key TEXT, genre_f32_le BLOB)")
            for i in range(100):
                x=tuple(0.5+0.11*((i*7+j*11)%29)+0.001*i*j for j in range(23))
                mood=tuple(0.1+0.002*i+0.0004*j+0.001*x[j%23]
                           for j in range(56))
                genre=tuple(0.03+0.0001*i*(j%7)+0.00003*j+
                            0.0002*x[(j*3)%23] for j in range(87))
                self.development.append((f"OLD-TRAIN-{i:03d}",x,mood))
                con.execute("INSERT INTO paired_tracks VALUES (?,?)",
                            (f"OLD-TRAIN-{i:03d}",
                             struct.pack("<87f",*genre)))
            con.commit()
        self.new_bliss=[
            tuple(0.7+0.14*((i*13+j*5)%31)+0.001*i*j for j in range(23))
            for i in range(240)
        ]
        self.native={}
        for i,key in enumerate(self.keys):
            x=self.new_bliss[i]
            # De-correlated but finite variation in all target views.
            mood=tuple(0.11+0.0018*i+0.0005*j+0.0015*x[j%23]
                       for j in range(56))
            genre=tuple(0.03+0.00014*i*(j%7)+0.00006*j+
                        0.0003*x[(j*3)%23] for j in range(87))
            theta=0.01*(i+1)
            embedding=[math.cos(theta),math.sin(theta)]+[0.0]*1278
            self.native[key]={
                "moodtheme":mood,"genre":genre,"embedding":embedding}
        self.protocol.write_text(json.dumps({
            "schema":r6.PROTOCOL,
            "locked_before_new_240_essentia_inference":True,
            "development_songs":100,
            "source_identity_group_disjoint_future_songs":240,
            "hyperparameters":{
                "no_tuning_on_new_teacher_or_human_labels":True,
                "moodtheme_teacher_dimensions":56
            }
        }))
        self.plan_data={
            "schema":r6.PLAN_SCHEMA,"songs":240,
            "old_grouped_db_sha256":_sha(self.old),
            "source_bliss_db_sha256":_sha(self.bliss),
            "private_r5_manifest_sha256":_sha(self.manifest),
            "manifest_sha256":hashlib.sha256(("".join(
                k+"\n" for k in sorted(self.keys))).encode()).hexdigest(),
            "private_source_audio_sha256_by_key":{k:"0"*64 for k in self.keys}
        }
        (self.plan/"private-scan-plan.json").write_text(json.dumps(self.plan_data))

    def _run(self):
        with patch.object(r6,"_old_grouped_rows",
                          return_value=(self.development,"a"*64)), \
             patch.object(r6,"_load_new_bliss",
                          return_value=(self.keys,self.new_bliss)), \
             patch.object(r6,"_native_rows",return_value=self.native):
            return r6.evaluate(self.plan,self.old,self.bliss,
                               self.manifest,self.protocol)

    def test_old_100_fixed_fit_new_240_proxy_report_has_no_private_rows(self):
        result=self._run()
        self.assertEqual(result["status"],
            "EXTERNAL_COHORT_TEACHER_PROXY_NOT_HUMAN_MUSICAL_VALIDATION")
        self.assertEqual(result["new_song_unordered_pairs"],28680)
        self.assertEqual(result["old_development_songs_used_to_fit"],100)
        self.assertFalse(result["new_song_teacher_labels_used_in_fitting"])
        self.assertTrue(result["WP1_and_WP2_winners_not_determined"])
        self.assertFalse(result["human_similarity_quality_measured"])
        for head in ("moodtheme_teacher_output_mae","genre_teacher_output_mae"):
            self.assertGreater(result[head]["train_mean_baseline"],0)
            self.assertGreaterEqual(result[head]["bliss_only_fixed_ridge"]
              if head.startswith("mood") else result[head]["old_train_only_pls_2"],0)
        for name,values in result["pairwise_spearman_to_teachers"].items():
            self.assertTrue(-1<=values["vs_genreteacher_euclidean"]<=1,name)
            self.assertTrue(-1<=values["vs_moodteacher_euclidean"]<=1,name)
        report=json.dumps(result)
        self.assertNotIn("Fictional New Artist",report)
        self.assertNotIn("OLD-TRAIN",report)
        self.assertNotIn(str(self.root),report)
        self.assertEqual(len(result["pairwise_spearman_to_teachers"]),7)

    def test_protocol_tamper_fails_before_fitting(self):
        doc=json.loads(self.protocol.read_text())
        doc["hyperparameters"]["no_tuning_on_new_teacher_or_human_labels"]=False
        self.protocol.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,"Frozen evaluation protocol"):
            self._run()

    def test_future_manifest_and_old_source_drift_block(self):
        self.old.write_bytes(b"changed old teacher DB")
        with self.assertRaisesRegex(ValueError,"Old teacher development DB changed"):
            self._run()

    def test_no_model_weights_or_listening_labels_written(self):
        self._run()
        self.assertEqual([p.name for p in self.plan.iterdir()],
                         ["private-scan-plan.json"])
        self.assertFalse((self.root/"model-weights.json").exists())


if __name__=="__main__":
    unittest.main()
