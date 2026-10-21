"""Synthetic artist-connected MTT holdout feasibility tests (no audio)."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "audit_mtt_groups", ROOT / "audit_magnatagatune_groups.py")
groups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groups)


class ArtistGroupsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.clips = self.root / "clips.csv"
        self.comparisons = self.root / "comparisons.csv"
        self.write_data()

    def write_data(self, shared=False):
        source = io.StringIO(newline="")
        wr = csv.writer(source)
        wr.writerow(["clip_id", "track_number", "title", "artist", "album",
                     "url", "segmentStart", "segmentEnd", "original_url", "mp3_path"])
        for ident in range(1, 25):
            artist = f"Artist {ident}"
            if shared and ident == 7:
                artist = "Artist 1"
            wr.writerow([ident, ident, f"Title {ident}", artist,
                         "Album", "url", 0, 30, "orig", f"{ident}.mp3"])
        self.clips.write_text(source.getvalue(), encoding="utf-8")
        source = io.StringIO(newline="")
        wr = csv.writer(source)
        wr.writerow(["clip1_id", "clip2_id", "clip3_id",
                     "clip1_numvotes", "clip2_numvotes", "clip3_numvotes",
                     "clip1_mp3_path", "clip2_mp3_path", "clip3_mp3_path"])
        for index in range(8):
            a, b, c = (str(index*3+i) for i in (1, 2, 3))
            votes = ("9", "1", "1") if index < 4 else ("4", "4", "3")
            wr.writerow([a,b,c,*votes,f"{a}.mp3",f"{b}.mp3",f"{c}.mp3"])
        self.comparisons.write_text(source.getvalue(), encoding="utf-8")

    def test_holdout_excludes_previously_scored_artist_groups(self):
        report = groups.audit(self.comparisons, self.clips, 20261021)
        self.assertEqual(report["unique_unordered_triplets"], 8)
        self.assertEqual(report["artist_components"], 8)
        self.assertEqual(report["forced_development"]["previous_smoke_triplets"], 4)
        self.assertEqual(report["forced_development"]["artist_components"], 4)
        self.assertTrue(report["holdout_candidate"]["possible_artist_disjoint_holdout"])
        self.assertEqual(report["holdout_candidate"]["heldout_unique_triplets"], 2)
        self.assertEqual(report["holdout_candidate"]["development_unique_triplets"], 6)
        self.assertEqual(len(report["holdout_candidate"]["component_selection_sha256"]),64)
        self.assertNotIn("Artist 1", json.dumps(report))

    def test_shared_artist_components_are_joined(self):
        self.write_data(shared=True)
        report = groups.audit(self.comparisons, self.clips)
        self.assertEqual(report["artist_components"], 7)
        self.assertEqual(report["largest_component_triplets"], 2)
        self.assertTrue(report["holdout_candidate"]["heldout_unique_triplets"] >= 1)

    def test_repeat_vote_rows_do_not_add_independent_triplets(self):
        rows = self.comparisons.read_text(encoding="utf-8").splitlines()
        self.comparisons.write_text("\n".join(rows+[rows[1]])+"\n", encoding="utf-8")
        report = groups.audit(self.comparisons, self.clips)
        self.assertEqual(report["ordered_comparison_rows"], 9)
        self.assertEqual(report["unique_unordered_triplets"], 8)


if __name__ == "__main__":
    unittest.main()
