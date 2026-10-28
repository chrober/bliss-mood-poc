#!/usr/bin/env python3
"""Read 3 local consecutive multipart ZIP files without concatenating them.

The 2.77 GiB publisher archive can be staged ONCE on a runner and
individual clips read directly via seekable byte ranges. No extraction
of the entire archive, public uploads, caches or API round trips per MP3.
"""
from __future__ import annotations
from pathlib import Path
import time


class LocalMultipartRanges:
    def __init__(self, parts: list[Path], expected_lengths: list[int]):
        if len(parts) != 3 or len(expected_lengths) != 3:
            raise ValueError("Three ZIP byte ranges required")
        if any(not f.is_file() for f in parts):
            raise FileNotFoundError("Missing local multipart ZIP file")
        real_sizes = [f.stat().st_size for f in parts]
        if real_sizes != expected_lengths or any(x < 1024 for x in real_sizes):
            raise ValueError("Local archive sizes differ from official HTTP 206 preflight")
        self.parts = parts
        self.part_sizes = real_sizes
        self.total_bytes = 0
        self.requests = 0
        self.min_request_spacing_seconds = 0
        self.range_pacing_sleep_seconds = 0.0

    def read(self, start: int, length: int) -> bytes:
        if length < 1 or length > 8 * 1024 * 1024 + 10000:
            raise ValueError("Bounded local ZIP read size violation")
        if start < 0 or start + length > sum(self.part_sizes):
            raise ValueError("Local ZIP seek outside concatenated stream")
        cursor = start
        left = length
        offset = 0
        result = bytearray()
        for part, size in zip(self.parts, self.part_sizes):
            boundary = offset + size
            if cursor >= boundary:
                offset = boundary
                continue
            take = min(left, boundary-cursor)
            with part.open("rb") as f:
                f.seek(cursor-offset)
                chunk = f.read(take)
            if len(chunk) != take:
                raise ValueError("Truncated staged ZIP part")
            result.extend(chunk)
            self.requests += 1
            cursor += take
            left -= take
            offset = boundary
            if not left:
                break
        if left:
            raise ValueError("Incomplete cross-part ZIP read")
        self.total_bytes += length
        return bytes(result)
