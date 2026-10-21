"""Offline tests of human odd-one-out majority/coverage without audio."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_magnatagatune_votes.py"
spec = importlib.util.spec_from_file_location("audit_mtt_votes", SCRIPT)
mtt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mtt)


class MttVoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clips = self.root / "clips.csv"
        self.comparisons = self.root / "comp.csv"
        self.create_clips()
        self.create_comparisons()

    def create_clips(self):
        s = io.StringIO(newline="")
        wr = csv.writer(s)
        wr.writerow(mtt.CLIP_FIELDS)
        for i in range(1, 7):
            wr.writerow([str(i), str(i), f"Title {i}", f"Artist {i}",
                         "Album", "url", "0", "30", "original",
                         f"a/{i}.mp3"])
        self.clips.write_text(s.getvalue(), encoding="utf-8")

    def create_comparisons(self, malformed=False):
        s = io.StringIO(newline="")
        wr = csv.writer(s)
        wr.writerow(mtt.COMPARISON_FIELDS)
        for i in range(400):
            vote = ("5", "2", "1") if i % 2 == 0 else ("3", "3", "2")
            wr.writerow(["1","2","3", *vote,
                         "a/1.mp3","a/2.mp3",
                         "BAD/3.mp3" if malformed else "a/3.mp3"])
        self.comparisons.write_text(s.getvalue(), encoding="utf-8")

    def test_majorities_ties_and_no_private_track_metadata(self):
        r = mtt.evaluate(self.comparisons, self.clips)
        self.assertEqual(r["questions"], 400)
        self.assertEqual(r["total_human_votes"], 3200)
        self.assertEqual(r["majority_vote"]["questions_with_tied_top_votes"], 200)
        self.assertEqual(r["majority_vote"]["questions_with_strict_absolute_majority"], 200)
        self.assertEqual(r["audio_requirements"]["distinct_clip_ids_in_questions"], 3)
        self.assertEqual(r["majority_vote"]["questions_with_unique_ge_70pct_consensus"], 0)
        self.assertEqual(len(r["hashes"]["comparisons_sha256"]), 64)
        self.assertNotIn("Artist 1", json.dumps(r))
        self.assertNotIn("a/1.mp3", json.dumps(r))

    def test_inconsistent_audio_paths_fail_closed(self):
        self.create_comparisons(malformed=True)
        with self.assertRaisesRegex(ValueError, "paths mismatch"):
            mtt.evaluate(self.comparisons, self.clips)

    def test_clip_reference_does_not_exist(self):
        txt = self.comparisons.read_text(encoding="utf8")
        self.comparisons.write_text(txt.replace("1,2,3,", "1,2,999,", 1),
                                    encoding="utf8")
        with self.assertRaisesRegex(ValueError, "missing clip"):
            mtt.evaluate(self.comparisons, self.clips)


if __name__ == "__main__":
    unittest.main()
