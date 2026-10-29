"""Offline regression: cache EXACTLY 1019 MTT MP3s, CRC vs publisher ZIP."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from mtt_selected_clip_cache import (
    build, verify, resolve_members, key_name, SelectedClipCache,
)
from audit_magnatagatune_archive import zip_member_directory


class SelectedClipResearchCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.cache = self.folder / "small-research-only-cache.zip"
        writer = io.BytesIO()
        with zipfile.ZipFile(writer, "w", compression=zipfile.ZIP_STORED) as archive:
            for ident in range(1, 1020):
                archive.writestr(
                    f"mp3/{ident:06d}.mp3",
                    b"ID3" + bytes([ident % 251]) * (900 + ident % 80),
                )
        self.original = writer.getvalue()
        length = len(self.original)
        first = length // 3
        second = length // 3
        self.sizes = [first, second, length - first - second]
        parts = [
            self.original[:first],
            self.original[first:first + second],
            self.original[first + second:],
        ]
        self.parts = []
        for number, part in enumerate(parts, 1):
            path = self.folder / f"mp3.zip.{number:03d}"
            path.write_bytes(part)
            self.parts.append(path)
        self.tail = self.folder / "tail.bin"
        self.tail.write_bytes(self.original[-150000:])
        self.members, _ = zip_member_directory(self.tail, self.sizes)
        self.required = resolve_members(
            {f"{ident:06d}.mp3" for ident in range(1, 1020)},
            self.members,
        )

    def test_cache_is_complete_compact_and_verified_against_official_crc(self):
        result = build(self.cache, self.required, self.parts, self.sizes)
        self.assertEqual(result["cached_clip_count"], 1019)
        self.assertEqual(result["fully_verified_uncompressed_audio_bytes"] > 0, True)
        self.assertEqual(verify(self.cache, self.required)["cached_clip_count"], 1019)
        with SelectedClipCache(self.cache, self.required) as source:
            data = source.read_clip("000001.mp3")
            self.assertTrue(data.startswith(b"ID3"))
            self.assertEqual(source.clips_read, 1)
            self.assertEqual(source.bytes_read, len(data))
            with self.assertRaises(ValueError):
                source.read_clip("not-allowed.mp3")
        with zipfile.ZipFile(self.cache) as archive:
            self.assertEqual(len(archive.namelist()), 1019)
            self.assertTrue(all(name.startswith("audio/") for name in archive.namelist()))
            self.assertNotIn("000001.mp3", str(archive.namelist()))
            self.assertEqual(archive.getinfo(key_name("000001.mp3")).compress_type,
                             zipfile.ZIP_STORED)
        with self.assertRaises(FileExistsError):
            build(self.cache, self.required, self.parts, self.sizes)

    def test_remote_sparse_builder_uses_existing_crc_and_bounds_without_network(self):
        from mtt_local_archive import LocalMultipartRanges

        paths = self.parts
        class SyntheticHTTP206:
            def __init__(self, sizes):
                self.source = LocalMultipartRanges(paths, sizes)
                self.requests = 0
                self.total_bytes = 0

            def read(self, start, length):
                self.requests += 1
                self.total_bytes += length
                return self.source.read(start, length)

        with patch("benchmark_magnatagatune.RangeFetcher", SyntheticHTTP206):
            result = build(self.cache, self.required, None, self.sizes,
                           remote_range_source=True)
        self.assertEqual(result["source_mode"], "sparse_crc_checked_http_ranges")
        self.assertGreaterEqual(result["range_requests"], 1019)
        self.assertEqual(result["cached_clip_count"], 1019)
        self.assertEqual(verify(self.cache, self.required)["cached_clip_count"], 1019)
        with self.assertRaises(FileExistsError):
            build(self.cache, self.required, None, self.sizes,
                  remote_range_source=True)

    def test_remote_and_local_archive_sources_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            build(self.cache, self.required, self.parts, self.sizes,
                  remote_range_source=True)
        with self.assertRaises(ValueError):
            build(self.cache, self.required, None, self.sizes)

    def test_incomplete_cache_is_rejected(self):
        with zipfile.ZipFile(self.cache, "w") as z:
            z.writestr(key_name("000001.mp3"), b"ID3")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify(self.cache, self.required)

    def test_changed_official_crc_is_rejected(self):
        build(self.cache, self.required, self.parts, self.sizes)
        one = self.required["000001.mp3"]
        import copy
        corrupted = copy.copy(one)
        corrupted.CRC = (one.CRC + 1) & 0xffffffff
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            verify(self.cache, {**self.required, "000001.mp3": corrupted})


if __name__ == "__main__":
    unittest.main()
