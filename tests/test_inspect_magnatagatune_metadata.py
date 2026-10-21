"""Offline synthetic tests for cheap MTT schema inventory and safety."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_magnatagatune_metadata.py"
spec = importlib.util.spec_from_file_location("inspect_mtt", SCRIPT)
mtt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mtt)


class MttSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.comparisons = root / "comparisons_final.csv"
        self.clips = root / "clip_info_final.csv"
        self.comparisons.write_text(
            "clip1,clip2,clip3,outlier\n"
            + "".join(f"{i},{i+1},{i+2},{i % 3}\n" for i in range(105)),
            encoding="utf-8-sig"
        )
        self.clips.write_text(
            "clip_id;artist;path\n"
            + "".join(f"{i};Private Artist {i};track_{i}.mp3\n" for i in range(1003)),
            encoding="utf-8"
        )

    def test_inventory_is_aggregate_and_audio_free(self):
        report = mtt.inspect(self.comparisons, self.clips)
        self.assertEqual(report["comparison_data"]["rows"], 105)
        self.assertEqual(report["clip_data"]["rows"], 1003)
        self.assertEqual(report["clip_data"]["delimiter"], "semicolon")
        self.assertEqual(report["comparison_data"]["fields"][0], "clip1")
        self.assertEqual(len(report["clip_data"]["sha256"]), 64)
        self.assertIn("not_yet_verified", report["status"])
        data = json.dumps(report)
        self.assertNotIn("Private Artist", data)
        self.assertNotIn("track_1002.mp3", data)

    def test_reject_broken_or_too_small_file(self):
        self.comparisons.write_text("a,b,c\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Malformed"):
            mtt.inspect(self.comparisons, self.clips)
        self.comparisons.write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected at least"):
            mtt.inspect(self.comparisons, self.clips)

    def test_no_duplicate_headers(self):
        self.comparisons.write_text(
            "clip,clip\n" + "1,2\n" * 101, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            mtt.inspect(self.comparisons, self.clips)


if __name__ == "__main__":
    unittest.main()
