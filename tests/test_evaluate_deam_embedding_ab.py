"""Synthetic DEAM same-song embedding/head paired VA correlation tests (offline)."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import zipfile
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import benchmark_deam as deam
import evaluate_deam_embedding_ab as ab


class DEAMPairedTests(unittest.TestCase):
    def setUp(self):
        self.ids=[str(i) for i in range(1,7)]+[str(i) for i in range(2001,2007)]
        self.labels={id:(2 + ix*.31,3 + (ix*7%11)*.35)
                     for ix,id in enumerate(self.ids)}
        self.vectors={}
        for ix,id in enumerate(self.ids):
            # Non-constant direct Cosine and classifier Cosine, each valid.
            unit=[0.0]*16
            unit[ix]=.8
            unit[(ix+3)%16]=.6
            self.vectors[id]={"embedding":unit,
                              "moodtheme":[.04+(j==ix)*.5+(j==((ix+3)%16))*.2
                                           for j in range(16)],
                              "genre":[.03+(j==ix)*.4+j*.0001
                                       + .0007*(ix+1)*((j+ix)%3) for j in range(16)]}

    def test_same_queries_and_common_denominator(self):
        a=ab.paired_va(self.vectors,self.ids,self.labels,seed=20261021,replicates=100)
        self.assertEqual(a["common_candidate_count_per_query"],11)
        self.assertEqual(a["policy"]["fixed_query_denominator"],12)
        self.assertEqual(a["policy"]["strata_counts"],
                         {"earlier_excerpt":6,"full_song_2015":6})
        for m,row in a["methods"].items():
            with self.subTest(m=m):
                self.assertEqual(row["query_denominator"],12)
                self.assertEqual(row["queries_complete"],12)
                self.assertEqual(row["queries_abstained"],0)
                self.assertEqual(row["query_coverage"],1)
                self.assertTrue(all(-1<=s<=1 for s in row["axes"].values()))
        for baseline in a["paired_differences"]:
            for axis in ab.AXES:
                d=a["paired_differences"][baseline][axis]
                self.assertEqual(d["paired_queries"],12)
                self.assertEqual(len(d["shared_stratified_query_95pct_sensitivity"]),2)
        serialized=json.dumps(a)
        self.assertNotIn("DEAM/1.mp3",serialized)
        self.assertNotIn('"1":',serialized)

    def test_one_collection_subcohort_and_shared_candidate_abstention(self):
        subset=self.ids[:6]
        result=ab.paired_va({k:self.vectors[k] for k in subset},
                            subset,self.labels,seed=1,replicates=100)
        self.assertEqual(result["common_candidate_count_per_query"],5)
        self.assertEqual(result["policy"]["strata_counts"],{"earlier_excerpt":6})
        invalid={key:dict(value) for key,value in self.vectors.items()}
        invalid[self.ids[0]]["embedding"]=[0.]*16
        result=ab.paired_va(invalid,self.ids,self.labels,seed=1,replicates=100)
        self.assertEqual(result["methods"]["embedding_cosine"]["queries_abstained"],12)
        self.assertEqual(result["methods"]["embedding_cosine"]["query_denominator"],12)
        self.assertEqual(result["methods"]["mood_cosine"]["queries_complete"],12)
        self.assertEqual(result["methods"]["embedding_cosine"]["axes"]["valence_arousal"],0.)

    def test_sample_sha_replays_original_deam_backslash_n_contract(self):
        ids = ["1", "2", "2001", "2002"]
        # Original DEAM v1 serializer: two literal ASCII chars (backslash, n).
        reference = hashlib.sha256(
            (r"\n".join(ids) + r"\n").encode("ascii")
        ).hexdigest()
        changed = hashlib.sha256(
            ("\n".join(ids) + "\n").encode("ascii")
        ).hexdigest()
        self.assertEqual(ab.sample_hash(ids), reference)
        self.assertNotEqual(ab.sample_hash(ids), changed)

    def test_frozen_cohort_fingerprint_and_protocol(self):
        ids=[str(i) for i in range(1,198)]+[str(i) for i in range(2001,2044)]
        labels={id:(4.,5.) for id in ids}
        ab.validate_selected(ids,labels,ab.sample_hash(ids))
        with self.assertRaisesRegex(ValueError,"fingerprint changed"):
            ab.validate_selected(ids,labels,ab.SAMPLE_SHA)
        labels.pop(ids[0])
        with self.assertRaisesRegex(ValueError,"Missing song-level"):
            ab.validate_selected(ids,labels,ab.sample_hash(ids))

    def test_same_encoder_pass_is_opt_in_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            aud=root/"audio.zip"
            with zipfile.ZipFile(aud,"w") as archive:
                archive.writestr("DEAM_audio/MEMD_audio/1.mp3",b"x"*2200)
            def fake_run(command,**kwargs):
                if "--embedding-out" in command:
                    Path(command[command.index("--embedding-out")+1]).write_text("{}")
                return SimpleNamespace(returncode=0,stderr="")
            with patch.object(deam.subprocess,"run",side_effect=fake_run) as run:
                deam.run_inference(Path("/bin/true"),root,aud,["1"],
                                   {"1":"DEAM_audio/MEMD_audio/1.mp3"},root/"one.db")
                self.assertNotIn("--embedding-out",run.call_args.args[0])
                deam.run_inference(Path("/bin/true"),root,aud,["1"],
                                   {"1":"DEAM_audio/MEMD_audio/1.mp3"},root/"two.db",
                                   root/"private")
                self.assertIn("--embedding-out",run.call_args.args[0])
                self.assertIn("DEAM/1.mp3",run.call_args.args[0])
                with self.assertRaises(FileExistsError):
                    deam.run_inference(Path("/bin/true"),root,aud,["1"],
                                       {"1":"DEAM_audio/MEMD_audio/1.mp3"},root/"three.db",
                                       root/"private")


if __name__=="__main__":
    unittest.main()
