#!/usr/bin/env python3
"""Bounded HTTP byte-range MP3 reader for the verified MTT multipart ZIP.

Read a local ZIP header and *only* the referenced member's compressed bytes
from mp3.zip.001/.002/.003, including cross-volume entries. Reject ignored
ranges, encryption, oversized payloads, zip-slip and CRC mismatches. Research
audio is returned in memory to a caller that writes a temporary file;
never store the original archive or upload MP3s as GitHub artifacts.
"""
from __future__ import annotations

from bisect import bisect_right
import re
import struct
import zlib
from urllib.request import Request, urlopen
import zipfile

BASE = "https://mirg.city.ac.uk/datasets/magnatagatune/"
LOCAL = struct.Struct("<IHHHHHIIIHH")
RANGE_RE = re.compile(r"bytes (\d+)-(\d+)/(\d+)")
MAX_CLIP_BYTES = 8 * 1024 * 1024


class ShardRangeReader:
    def __init__(self, part_sizes: list[int], base: str = BASE, transport=None):
        if (len(part_sizes) != 3 or any(not isinstance(x, int) or
                                        x < 1000 for x in part_sizes)):
            raise ValueError("Require valid positive sizes of three MTT ZIP shards")
        self.sizes = part_sizes
        self.base = base
        self.bounds = [0, part_sizes[0], part_sizes[0]+part_sizes[1],
                       sum(part_sizes)]
        self.transport = transport
        self.bytes_downloaded = 0
        self.requests = 0

    def _http_read(self, volume: int, offset: int, count: int) -> bytes:
        if self.transport is not None:
            result = self.transport(volume, offset, count)
        else:
            url = self.base + f"mp3.zip.{volume+1:03d}"
            req = Request(url, headers={
                "Range": f"bytes={offset}-{offset+count-1}",
                "Accept-Encoding": "identity",
            })
            with urlopen(req, timeout=90) as response:
                if response.status != 206:
                    raise ValueError("MTT host ignored range; refusing full audio download")
                match = RANGE_RE.fullmatch(
                    response.headers.get("Content-Range", "").strip()
                )
                if not match:
                    raise ValueError("Missing MTT Content-Range")
                start, end, total = map(int, match.groups())
                if (start, end, total) != (
                    offset, offset+count-1, self.sizes[volume]
                ):
                    raise ValueError("Unexpected HTTP partial content offsets")
                result = response.read(count+1)
        if len(result) != count:
            raise ValueError("Incomplete or oversized MTT byte-range result")
        self.requests += 1
        self.bytes_downloaded += len(result)
        return result

    def read(self, absolute_offset: int, size: int) -> bytes:
        if (absolute_offset < 0 or size <= 0 or size > MAX_CLIP_BYTES or
            absolute_offset+size > self.bounds[-1]):
            raise ValueError("Invalid or unbounded remote ZIP byte range")
        pieces = []
        remaining = size
        current = absolute_offset
        while remaining:
            volume = bisect_right(self.bounds, current)-1
            if volume < 0 or volume > 2:
                raise ValueError("Bad ZIP archive volume offset")
            length = min(remaining, self.bounds[volume+1]-current)
            if length <= 0:
                raise ValueError("Zero-progress ZIP range")
            pieces.append(self._http_read(
                volume, current-self.bounds[volume], length
            ))
            current += length
            remaining -= length
        return b"".join(pieces)


def mp3_member_bytes(reader: ShardRangeReader, info: zipfile.ZipInfo) -> bytes:
    if info.flag_bits & 0x01:
        raise ValueError("Encrypted MTT entries are unsupported")
    if info.file_size > MAX_CLIP_BYTES or info.compress_size > MAX_CLIP_BYTES:
        raise ValueError("MTT clip too large for bounded member retrieval")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise ValueError("Unexpected ZIP compression format")
    header = reader.read(info.header_offset, LOCAL.size)
    fields = LOCAL.unpack(header)
    signature, version, flag, method, mtime, mdate, crc, compressed, original, namelen, extralen = fields
    if signature != 0x04034b50 or flag & 1 or method != info.compress_type:
        raise ValueError("MTT local ZIP header disagrees with directory")
    name_start = info.header_offset + LOCAL.size
    # Verify local name bytes, not just central directory offsets.
    if namelen > 2048 or extralen > 65535:
        raise ValueError("Suspicious ZIP local name/extra length")
    local_name = reader.read(name_start, namelen)
    expected = info.orig_filename.encode("utf-8" if info.flag_bits & 0x800 else "cp437")
    if local_name != expected:
        raise ValueError("ZIP local name differs from verified central directory")
    start = name_start + namelen + extralen
    compressed_data = reader.read(start, info.compress_size)
    if info.compress_type == zipfile.ZIP_STORED:
        output = compressed_data
    else:
        decoder = zlib.decompressobj(-15)
        output = decoder.decompress(compressed_data, MAX_CLIP_BYTES+1)
        output += decoder.flush()
        if not decoder.eof or decoder.unused_data:
            raise ValueError("Broken ZIP deflate member")
    if (len(output) != info.file_size or len(output) > MAX_CLIP_BYTES or
        zlib.crc32(output) & 0xffffffff != info.CRC):
        raise ValueError("MTT member failed ZIP length/CRC verification")
    if not output:
        raise ValueError("Empty MTT MP3 clip")
    return output
