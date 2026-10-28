"""Synthetic multipart ZIP tail reader and official MTT reference matching."""
import csv
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location(
    "audit_magnatagatune_archive",
    SCRIPT_DIR / "audit_magnatagatune_archive.py",
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class MttArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.clips = self.root / "clip_info_final.csv"
        self.comparisons = self.root / "comparisons_final.csv"
        self.tail = self.root / "tail.bin"

        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(audit.CLIP_FIELDS if hasattr(audit, "CLIP_FIELDS") else [
            "clip_id", "track_number", "title", "artist", "album",
            "url", "segmentStart", "segmentEnd", "original_url", "mp3_path"
        ])
        for number in (1, 2, 3):
            writer.writerow([
                str(number), "1", f"Title {number}", f"Artist {number}",
                "Album", "url", "0", "30", "original", f"{number}.mp3"
            ])
        self.clips.write_text(out.getvalue(), encoding="utf-8")

        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(audit.COMPARISON_FIELDS)
        for _ in range(533):
            writer.writerow(["1", "2", "3", "6", "1", "1",
                             "1.mp3", "2.mp3", "3.mp3"])
        self.comparisons.write_text(out.getvalue(), encoding="utf-8")

        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_STORED) as z:
            for i in range(1, 126):
                z.writestr(f"mp3/{i}.mp3", b"x" * (400 + i))
        self.content = memory.getvalue()
        n = len(self.content)
        self.parts = [n // 30, n // 30, n - 2 * (n // 30)]
        self.tail.write_bytes(self.content[-min(20000, self.parts[2]):])

    def test_read_multipart_central_directory_without_audio(self):
        result = audit.evaluate(self.tail, self.parts, self.comparisons, self.clips)
        self.assertEqual(
            result["status"], "PASS_all_required_clip_paths_in_zip_central_directory")
        self.assertEqual(result["zip"]["zip_nondirectory_entries"], 125)
        self.assertEqual(result["metadata_questions"], 533)
        self.assertEqual(result["unique_unordered_clip_triplets"], 1)
        self.assertEqual(result["triplet_rows_with_permuted_or_repeated_clip_sets"], 532)
        self.assertEqual(result["required_unique_mp3s"], 3)
        self.assertEqual(result["audio_member_matches"]["unique_path_suffix"], 3)
        self.assertEqual(result["audio_member_matches"]["missing"], 0)
        self.assertGreater(result["required_compressed_mp3_bytes"], 0)
        self.assertNotIn("Title 1", str(result))
        self.assertNotIn("mp3/1.mp3", str(result))

    def test_missing_file_fails_validation(self):
        with zipfile.ZipFile(io.BytesIO(self.content)) as z:
            pass
        text = self.clips.read_text(encoding="utf-8").replace(
            "3.mp3", "missing_3.mp3"
        )
        self.clips.write_text(text, encoding="utf-8")
        comps = self.comparisons.read_text(encoding="utf-8").replace(
            "3.mp3", "missing_3.mp3"
        )
        self.comparisons.write_text(comps, encoding="utf-8")
        result = audit.evaluate(self.tail, self.parts, self.comparisons, self.clips)
        self.assertEqual(result["audio_member_matches"]["missing"], 1)
        self.assertEqual(result["status"], "BLOCKED_incomplete_archive_membership")

    def test_tail_too_small_must_fail_closed(self):
        self.tail.write_bytes(self.content[-400:])
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            audit.evaluate(self.tail, self.parts, self.comparisons, self.clips)

    def test_path_traversal_cannot_match(self):
        with self.assertRaises(ValueError):
            audit.zip_path("../private.mp3")


if __name__ == "__main__":
    unittest.main()
