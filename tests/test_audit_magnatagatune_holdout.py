"""Pure metadata artist-disjoint holdout audit tests, synthetic MTT votes."""
import csv
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("mtt_holdout",SCRIPTS/"audit_magnatagatune_holdout.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class HoldoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.clips=self.root/"clips.csv"
        self.comparisons=self.root/"comparisons.csv"
        c=io.StringIO(newline="")
        writer=csv.writer(c)
        writer.writerow(["clip_id","track_number","title","artist","album",
                         "url","segmentStart","segmentEnd","original_url","mp3_path"])
        for i in range(1,19):
            writer.writerow([str(i),i,f"Track {i}",f"Artist {i}","Album","URL",
                             0,30,"original",f"mp3/{i}.mp3"])
        self.clips.write_text(c.getvalue(),encoding="utf-8")
        c=io.StringIO(newline="")
        w=csv.writer(c)
        w.writerow(["clip1_id","clip2_id","clip3_id","clip1_numvotes","clip2_numvotes",
                    "clip3_numvotes","clip1_mp3_path","clip2_mp3_path","clip3_mp3_path"])
        for start in range(1,18,3):
            ids=list(range(start,start+3))
            w.writerow([*ids,5,3,1,*(f"mp3/{i}.mp3" for i in ids)])
        self.comparisons.write_text(c.getvalue(),encoding="utf-8")

    def test_policy_determinism_and_counts(self):
        a=mod.evaluate(self.comparisons,self.clips)
        b=mod.evaluate(self.comparisons,self.clips)
        self.assertEqual(a["artist_disjoint_questions"], b["artist_disjoint_questions"])
        self.assertEqual(a["unique_unordered_triplets"],6)
        groups=a["artist_disjoint_questions"]
        self.assertEqual(sum(x["count"] for x in groups.values()),6)
        self.assertEqual(a["artist_component_graph"]["components"],6)
        self.assertIn("less_than_128", a["artist_hash_policy"])
        smoke = a["prior_four_triplet_smoke_exposure"]
        self.assertEqual(
            smoke["holdout_triplets_touching_smoke_artists"]
            + smoke["holdout_triplets_never_touched_by_smoke_artists"],
            a["artist_disjoint_questions"]["holdout"]["count"]
        )
        for cutoff in ("51", "85", "128"):
            design = a["candidate_artist_holdout_designs"][cutoff]
            self.assertEqual(sum(design["questions"].values()), 6)
            self.assertIn("NOT_tested", design["status"])
        self.assertEqual(a["artist_component_graph"]["triplets_in_largest_component"],1)
        self.assertNotIn("Artist 1",str(a))
        self.assertEqual(len(groups["holdout"]["sorted_triplet_id_sha256"]),64)
        self.assertTrue(all(mod.artist_bucket(f"artist {i}") in ("development","holdout")
                            for i in range(1,19)))

    def test_repeat_reordered_comparison_is_one_unique_triplet(self):
        text=self.comparisons.read_text(encoding="utf-8")
        text+="3,1,2,2,3,4,mp3/3.mp3,mp3/1.mp3,mp3/2.mp3\n"
        self.comparisons.write_text(text,encoding="utf-8")
        result=mod.evaluate(self.comparisons,self.clips)
        self.assertEqual(result["unique_unordered_triplets"],6)
        self.assertEqual(result["original_comparison_rows"],7)


if __name__=="__main__":
    unittest.main()
