"""Synthetic bounded ZIP central directory and MTT clip path tests; no network."""
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("probe_mtt_zip", SCRIPTS / "probe_magnatagatune_zip_index.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ZipDirectoryTests(unittest.TestCase):
    def make_archive(self):
        contents = io.BytesIO()
        with zipfile.ZipFile(contents, "w", compression=zipfile.ZIP_DEFLATED) as out:
            for i in range(100):
                out.writestr(f"mp3/0/song_{i:04}.mp3", b"audio" * (i + 1))
        return contents.getvalue()

    def test_small_range_lists_every_member(self):
        full = self.make_archive()
        tail = full[-8192:]
        names, stats = probe.directory_names(tail, len(full)-len(tail), len(full))
        self.assertEqual(len(names), 100)
        self.assertEqual(stats["zip_entries"], 100)
        self.assertEqual(stats["zip_directories"], 0)
        req = {"0/song_0000.mp3", "0/song_0001.mp3", "0/song_0002.mp3"}
        result = probe.audit(req, names, stats)
        self.assertEqual(result["path_mapping"], "mp3_prefix")
        self.assertEqual(result["required_unique_clips"], 3)

    def test_too_short_tail_fails_closed(self):
        full = self.make_archive()
        with self.assertRaisesRegex(ValueError, "central directory"):
            probe.directory_names(full[-100:], len(full)-100, len(full))

    def test_ambiguous_mapping_rejected(self):
        with self.assertRaisesRegex(ValueError, "unambiguous"):
            probe.audit({"a.mp3"}, {"a.mp3", "mp3/a.mp3"}, {})

    def test_missing_reference_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "unambiguous"):
            probe.audit({"0/song_0000.mp3", "0/not_present.mp3"},
                        {"mp3/0/song_0000.mp3"}, {})


if __name__ == "__main__":
    unittest.main()
