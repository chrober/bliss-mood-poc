"""Synthetic ONLY: blinded WP3 pilot uses old development, private new songs and sealed comparisons."""
from __future__ import annotations
from contextlib import closing, redirect_stdout
import io
import json
import math
from pathlib import Path
import sqlite3
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_prepare_wp3_independent_cohort import IndependentCohortTests
from test_run_local_bliss_essentia_teacher_study import _sha
import prepare_wp3_independent_cohort as planner
import prepare_wp3_blinded_bliss_student_pilot as pilot


class BlindStudentPilotTests(unittest.TestCase):
    def setUp(self):
        obj=IndependentCohortTests("test_deterministic_even_if_called_twice")
        obj.setUp()
        self.addCleanup(obj.doCleanups)
        self.obj=obj
        self.src=obj.x
        self.manifest_path=obj.x.root/"independent-manifest.json"
        self.spec_path=obj.x.root/"candidate-spec.json"
        self.out=obj.x.root/"private-pilot"
        with closing(sqlite3.connect(self.src.source.bliss)) as b, \
             closing(sqlite3.connect(self.src.snapshot)) as sn, \
             closing(sqlite3.connect(self.src.library)) as lm:
            for j in range(190):
                key=f"Private New Validation {j}/Track.flac"
                mbid=str(uuid.uuid5(uuid.NAMESPACE_DNS,"private-new-"+str(j)))
                artist=f"new-artist-{j}"
                album=15000+j
                tid=50000+j
                features=[0.1+((j*7+k*3)%47)/50 for k in range(23)]
                features[0]=float(50+j%140)
                features[2]=float((j*11)%47)
                b.execute('INSERT INTO TracksV2 VALUES ('+','.join('?'*24)+')',
                          (key,*features))
                sn.execute("INSERT INTO track_identity VALUES (?,?,?,?)",
                           (key,tid,f"unique-md5-{j}",mbid))
                sn.execute("INSERT INTO track_artist_identity VALUES (?,?,?)",
                           (key,"ARTIST",artist))
                lm.execute("INSERT INTO albums VALUES (?)",(album,))
                lm.execute("INSERT INTO tracks VALUES (?,?,?,?,?,?)",
                           (tid,f"unique-md5-{j}",mbid,album,0,1))
            b.commit()
            sn.commit()
            lm.commit()
        man,agg=planner.plan(self.src.source.bliss,self.src.snapshot,
                            self.src.library,self.obj.old,count=240,seed=20261030)
        self.assertEqual(agg["new_songs"],240)
        self.manifest_path.write_text(json.dumps(man),encoding="utf-8")
        spec={
            "schema":"wp3-frozen-hypothesis-spec-v1",
            "status":"EXPLORATORY_ARCHITECTURE_ONLY_NOT_TRAINED_MODEL",
            "candidate":{"teacher_head":"moodtheme","teacher_dimensions":56,
                         "input_feature_count":23,"ridge_alpha":10}
        }
        self.spec_path.write_text(json.dumps(spec),encoding="utf-8")
        self.old_rows=[]
        # Synthesized 100 old development points, distinct from *all* real
        # future candidate keys in this fixture. No heldout new pseudo-targets.
        for j in range(100):
            x=tuple(float((j*7+k*13)%67)/20.0 for k in range(23))
            y=tuple(float(0.01+sum(x[k]*(1+(d+k)%5) for k in range(23))/1000)
                    for d in range(56))
            self.old_rows.append((f"Private old development {j}",x,y))
        self.old_hash="c"*64

    def _run(self):
        return pilot.make_outputs(self.src.source.bliss,self.src.snapshot,
                                  self.src.library,self.obj.old,
                                  self.manifest_path,self.spec_path)

    def test_blind_pilot_uses_exact_distinct_songs_and_empty_labels(self):
        paths=(self.src.source.bliss,self.src.snapshot,self.src.library,self.obj.old)
        before=tuple(_sha(p) for p in paths)
        with patch.object(pilot,"_old_grouped_rows",
                          return_value=(self.old_rows,self.old_hash)):
            rows,model,audit,out=self._run()
        self.assertEqual(out["selected_blind_pairs"],24)
        self.assertEqual(out["new_source_disjoint_songs"],240)
        self.assertEqual(out["distinct_song_count"],48)
        self.assertEqual(out["sampling_strata_counts"],
                         {"raw_prefers":6,"student_prefers":6,"random":12})
        self.assertFalse(out["independent_perceptual_labels_available"])
        self.assertFalse(out["blind_sample_is_unbiased_population_estimate"])
        self.assertEqual(len({k for row in rows for k in
                              (row["left"],row["right"])}),48)
        self.assertTrue(all(row["similarity_0_to_5"]=="" for row in rows))
        self.assertEqual(len(model["scaler_mean"]),23)
        self.assertEqual(len(model["coef"]),(56))
        self.assertTrue(all(len(r)==23 for r in model["coef"]))
        self.assertEqual(len(model["intercept"]),56)
        self.assertEqual(len(audit["proposed_pairs"]),24)
        self.assertFalse(self.out.exists())
        self.assertEqual(tuple(_sha(p) for p in paths),before)
        for forbidden in ("Private old development", "Private New Validation",
                          str(self.src.root)):
            self.assertNotIn(forbidden,json.dumps(out))

    def test_deterministic_and_frozen_model(self):
        with patch.object(pilot,"_old_grouped_rows",
                          return_value=(self.old_rows,self.old_hash)):
            a=self._run()
            b=self._run()
        self.assertEqual(a,b)

    def test_tampered_manifest_does_not_allow_independence_bypass(self):
        document=json.loads(self.manifest_path.read_text(encoding="utf-8"))
        document["selected_songs"][0]["track_file"]="bogus"
        self.manifest_path.write_text(json.dumps(document),encoding="utf-8")
        with patch.object(pilot,"_old_grouped_rows",
                          return_value=(self.old_rows,self.old_hash)):
            with self.assertRaisesRegex(ValueError,"manifest does not match"):
                self._run()
        self.assertFalse(self.out.exists())

    def test_frozen_ridge_alpha_cannot_be_tuned(self):
        doc=json.loads(self.spec_path.read_text(encoding="utf-8"))
        doc["candidate"]["ridge_alpha"]=0.01
        self.spec_path.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"hypothesis mismatch"):
            self._run()

    def test_development_100_guard_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"exactly 100 unique"):
            pilot._old_grouped_rows(self.obj.old)

    def test_cli_private_creation_and_no_overwrite(self):
        args=[
            "blind-pilot","--bliss-db",str(self.src.source.bliss),
            "--repeat-identity-db",str(self.src.snapshot),
            "--lyrion-library-db",str(self.src.library),
            "--old-grouped-research-db",str(self.obj.old),
            "--new-private-manifest",str(self.manifest_path),
            "--frozen-spec",str(self.spec_path),"--out-dir",str(self.out)
        ]
        out=io.StringIO()
        with patch.object(pilot,"_old_grouped_rows",
                          return_value=(self.old_rows,self.old_hash)):
            with patch.object(sys,"argv",args),redirect_stdout(out):
                self.assertEqual(pilot.main(),0)
        result=json.loads(out.getvalue())
        self.assertEqual(result["selected_blind_pairs"],24)
        self.assertNotIn("Private New Validation",out.getvalue())
        self.assertNotIn(str(self.src.root),out.getvalue())
        self.assertTrue((self.out/"private-blind-pairs.csv").is_file())
        self.assertTrue((self.out/"private-frozen-student.json").is_file())
        self.assertTrue((self.out/"private-sealed-selection-audit.json").is_file())
        original=(self.out/"private-blind-pairs.csv").read_bytes()
        with patch.object(pilot,"_old_grouped_rows",
                          return_value=(self.old_rows,self.old_hash)):
            with patch.object(sys,"argv",args),redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as err:
                    pilot.main()
        self.assertEqual(err.exception.code,2)
        self.assertEqual((self.out/"private-blind-pairs.csv").read_bytes(),original)


if __name__=="__main__":
    unittest.main()
