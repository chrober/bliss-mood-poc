"""Offline synthetic multipart range and ZIP integrity tests (no network)."""
import importlib.util
import io
from pathlib import Path
import sys
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("mtt_range", SCRIPTS / "mtt_range_clip_reader.py")
mtt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mtt)


class MttRangeTests(unittest.TestCase):
    def make_source(self, compression):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=compression) as writer:
            writer.writestr("mp3/0/clip.mp3", b"F" * 5000 + b"AUDIO")
        whole = buf.getvalue()
        # Tiny artificial shard segments: the compressed body crosses them.
        sections = [whole[:42], whole[42:135], whole[135:]]
        with zipfile.ZipFile(io.BytesIO(whole)) as archive:
            info = archive.getinfo("mp3/0/clip.mp3")
        def fake_http(volume, offset, count):
            return sections[volume][offset:offset+count]
        reader = mtt.ShardRangeReader([len(x) for x in sections],
                                      transport=fake_http)
        return reader, info, sections

    def test_extract_stored_or_deflated_member_across_shards(self):
        for method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            with self.subTest(method=method):
                reader, info, _ = self.make_source(method)
                result = mtt.mp3_member_bytes(reader, info)
                self.assertEqual(result, b"F" * 5000 + b"AUDIO")
                self.assertGreater(reader.requests, 1)
                self.assertLess(reader.bytes_downloaded, 10000)

    def test_member_crc_failure_is_not_accepted(self):
        reader, info, parts = self.make_source(zipfile.ZIP_STORED)
        original = parts[1]
        changed = bytearray(original)
        changed[0] ^= 1
        parts[1] = bytes(changed)
        with self.assertRaisesRegex(ValueError, "CRC"):
            mtt.mp3_member_bytes(reader, info)

    def test_truncated_byte_range_is_rejected(self):
        reader, info, _ = self.make_source(zipfile.ZIP_STORED)
        reader.transport = lambda vol, off, size: b"Z" * max(0, size - 1)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            mtt.mp3_member_bytes(reader, info)

    def test_oversize_and_invalid_absolute_range(self):
        reader, info, _ = self.make_source(zipfile.ZIP_STORED)
        with self.assertRaisesRegex(ValueError, "Invalid or unbounded"):
            reader.read(0, mtt.MAX_CLIP_BYTES+1)
        with self.assertRaisesRegex(ValueError, "Invalid or unbounded"):
            reader.read(10**9, 10)


if __name__ == "__main__":
    unittest.main()
