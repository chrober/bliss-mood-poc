"""Synthetic no-network, no-audio tests for one official MTT member probe."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import probe_wp1_e2_mtt_member as p


class MemberProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-mtt-e2-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tail = self.root / "tail.bin"
        with self.tail.open("wb") as f:
            f.truncate(p.MAX_TAIL)
        self.comparisons = self.root / "comparisons.csv"
        self.clips = self.root / "clips.csv"
        self.comparisons.write_text("fictional test only", encoding="utf-8")
        self.clips.write_text("fictional test only", encoding="utf-8")
        self.sizes = [1_100_000_000, 1_100_000_000, 772_769_864]

    def test_one_clip_is_in_memory_and_only_counts_are_returned(self):
        public_path = "Fictional Artist/private source track.mp3"
        class Fetcher:
            def __init__(self, part_sizes):
                self.total_bytes = 512
                self.requests = 1
        def fake_digest(path):
            return (p.mtt.REGISTERED_MTT_COMPARISONS_SHA256
                    if path == self.comparisons
                    else p.mtt.REGISTERED_MTT_CLIPS_SHA256)
        with patch.object(p.mtt, "digest", side_effect=fake_digest), \
             patch.object(p, "zip_member_directory",
                          return_value=({public_path: object()}, {})), \
             patch.object(p, "needed_paths",
                          return_value=({public_path} | {
                              f"fictional-{i}" for i in range(1018)
                          }, 533, 346)), \
             patch.object(p, "resolve_members",
                          return_value={public_path: object()}), \
             patch.object(p.mtt, "RangeFetcher", Fetcher), \
             patch.object(p.mtt, "extract_mp3", return_value=b"fake audio"):
            output = p.check_one(self.tail, self.sizes,
                                 self.comparisons, self.clips)
        self.assertEqual(output["status"],
                         "ONE_OFFICIAL_MEMBER_RANGE_AND_ZIP_CRC_PASS")
        self.assertEqual(output["tested_clips"], 1)
        self.assertEqual(output["range_requests"], 1)
        self.assertFalse(output["all_1019_clips_accessible_proven"])
        self.assertFalse(output["global_pairwise_fusion_measured"])
        self.assertNotIn(public_path, json.dumps(output))

    def test_fail_closed_before_download_for_invalid_sources(self):
        with self.assertRaises(ValueError):
            p.check_one(self.tail, [100, 200, 300],
                        self.comparisons, self.clips)
        self.tail.unlink()
        with self.assertRaises(ValueError):
            p.check_one(self.tail, self.sizes, self.comparisons, self.clips)

    def test_error_output_never_leaks_selected_track(self):
        out = self.root / "result.json"
        cli = ["probe", "--tail", str(self.tail),
               "--part-sizes", *(str(x) for x in self.sizes),
               "--comparisons", str(self.comparisons),
               "--clips", str(self.clips), "--out", str(out)]
        with patch.object(sys, "argv", cli), \
             patch.object(p, "check_one", side_effect=RuntimeError(
                 "HTTP range failed for Fictional Artist/private song.mp3")), \
             redirect_stdout(StringIO()) as stdout:
            self.assertEqual(p.main(), 0)
        result=json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "RANGE_TRANSPORT_BLOCKED")
        self.assertNotIn("private song", stdout.getvalue())
        self.assertNotIn("private song", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
