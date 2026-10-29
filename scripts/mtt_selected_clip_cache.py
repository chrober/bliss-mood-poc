#!/usr/bin/env python3
"""Build/validate a small research-only cache of 1,019 licensed MTT MP3s.

Reads the official ZIP central directory from an 8-MiB HTTP tail.
On a cache miss, extracts ONLY clips referenced by human triplets
from three local publisher parts (no bulk extraction), CRC-checks
them and stores them losslessly in a single ~117-MB ZIP_STORED file.
On a hit, validates the COMPLETE package against the original ZIP
directory without downloading the multi-GiB source again.

Never publish this package as an Actions artifact or commit it to git.
The package contains third-party CC BY-NC-SA 3.0 research audio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import zipfile
import zlib

from audit_magnatagatune_archive import zip_member_directory, needed_paths
from mtt_local_archive import LocalMultipartRanges

MAX_PACKAGE_BYTES = 300 * 1024 * 1024
EXPECTED_REQUIRED_CLIPS = 1019
MAX_CLIP_BYTES = 20 * 1024 * 1024


def key_name(source_path: str) -> str:
    """Hide human-readable publisher path names in the cached ZIP listing."""
    return "audio/" + hashlib.sha256(
        ("MTT-required-clips-cache-v1\0" + source_path).encode("utf8")
    ).hexdigest() + ".mp3"


def resolve_members(source_paths: set[str], original_members: dict) -> dict[str, zipfile.ZipInfo]:
    """Use one-to-one, exact-or-unique-suffix source member mapping."""
    from benchmark_magnatagatune import member_lookup
    resolved = {}
    for path in sorted(source_paths):
        info = member_lookup(original_members, path)
        if info.is_dir() or info.file_size <= 0 or info.file_size > MAX_CLIP_BYTES:
            raise ValueError("Publisher referenced invalid/oversized MP3")
        if info.compress_size <= 0 or info.compress_size > 8 * 1024 * 1024:
            raise ValueError("Publisher referenced invalid/oversized compressed MP3")
        resolved[path] = info
    names = [key_name(path) for path in resolved]
    if len(set(names)) != len(resolved):
        raise ValueError("Clip cache member key collision")
    return resolved


def verify(cache: Path, required: dict[str, zipfile.ZipInfo],
           *, check_every_member: bool = True) -> dict:
    if not cache.is_file():
        raise FileNotFoundError("Selected-clip audio research cache missing")
    if cache.stat().st_size > MAX_PACKAGE_BYTES:
        raise ValueError("Research audio cache unexpectedly large")
    wanted = {key_name(path) for path in required}
    seen_bytes = 0
    with zipfile.ZipFile(cache, "r") as archive:
        existing = {item.filename for item in archive.infolist() if not item.is_dir()}
        if existing != wanted or len(archive.infolist()) != len(required):
            raise ValueError("Cached ZIP is incomplete or contains unexpected audio")
        for path, expected in required.items():
            item = archive.getinfo(key_name(path))
            if (item.compress_type != zipfile.ZIP_STORED
                    or item.file_size != expected.file_size
                    or item.CRC != expected.CRC):
                raise ValueError("Cached clip metadata differs from official source ZIP")
            if check_every_member:
                # zipfile.read also independently verifies the cache entry CRC.
                audio = archive.read(item)
                if len(audio) != expected.file_size or zlib.crc32(audio) != expected.CRC:
                    raise ValueError("Cached MP3 failed official-source CRC/length check")
                seen_bytes += len(audio)
    return {
        "cached_clip_count": len(required),
        "cache_file_bytes": cache.stat().st_size,
        "fully_verified_uncompressed_audio_bytes": seen_bytes,
        "verified_against_original_zip_crc": bool(check_every_member),
    }


class SelectedClipCache:
    """Read-only cache adapter for the actual Rust-v5 benchmark."""

    def __init__(self, cache: Path, required: dict[str, zipfile.ZipInfo]):
        verify(cache, required)
        self.archive = zipfile.ZipFile(cache, "r")
        self.required = required
        self.clips_read = 0
        self.bytes_read = 0
        self.total_bytes = 0
        self.requests = 0
        self.min_request_spacing_seconds = 0
        self.range_pacing_sleep_seconds = 0.0

    def read_clip(self, source_path: str) -> bytes:
        if source_path not in self.required:
            raise ValueError("Requested audio not in fixed MTT research cache manifest")
        expected = self.required[source_path]
        audio = self.archive.read(key_name(source_path))
        if len(audio) != expected.file_size or zlib.crc32(audio) != expected.CRC:
            raise ValueError("Cached MP3 CRC/length differs from source archive")
        self.clips_read += 1
        self.bytes_read += len(audio)
        return audio

    def close(self) -> None:
        self.archive.close()

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.close()


def build(cache: Path, required: dict[str, zipfile.ZipInfo],
          archive_parts: list[Path] | None, part_sizes: list[int],
          *, remote_range_source: bool = False) -> dict:
    if cache.exists():
        raise FileExistsError("Refuse overwrite of immutable research audio cache")
    if len(required) != EXPECTED_REQUIRED_CLIPS:
        raise ValueError("Cached audio cardinality differs from registered study")
    from benchmark_magnatagatune import extract_mp3, RangeFetcher
    if remote_range_source and archive_parts:
        raise ValueError('Select remote sparse ranges OR local source archive, never both')
    if not remote_range_source and not archive_parts:
        raise ValueError('Local cache build requires complete source archives')
    source = (RangeFetcher(part_sizes) if remote_range_source
              else LocalMultipartRanges(archive_parts, part_sizes))
    cache.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(cache, mode="x", allowZip64=True) as dest:
            for count, (path, info) in enumerate(sorted(required.items()), 1):
                audio = extract_mp3(info, source)  # original ZIP CRC validated
                # MP3 is already compressed: store losslessly without recompression.
                entry = zipfile.ZipInfo(key_name(path), date_time=(2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_STORED
                entry.external_attr = 0o600 << 16
                dest.writestr(entry, audio)
                if count % 100 == 0:
                    print(f"Curated MTT audio cache: {count}/{len(required)} clips", flush=True)
        data = verify(cache, required)
        if data["cache_file_bytes"] > MAX_PACKAGE_BYTES:
            raise ValueError("Created cache exceeds 300 MiB research bound")
        return {**data, "source_zip_bytes_read": source.total_bytes,
                "source_mode": "sparse_crc_checked_http_ranges" if remote_range_source
                               else "local_publisher_archive",
                "range_requests": source.requests if remote_range_source else 0}
    except BaseException:
        cache.unlink(missing_ok=True)
        raise


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("build", "verify"), required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--tail", type=Path, required=True)
    p.add_argument("--part-sizes", type=int, nargs=3, required=True)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--source-parts", type=Path, nargs=3)
    p.add_argument("--remote-range-source", action="store_true",
                   help="Build 1019 clips from bounded publisher HTTP 206 ranges only; no full ZIP parts")
    args = p.parse_args()
    if args.mode == "build" and bool(args.source_parts) == bool(args.remote_range_source):
        p.error("Choose exactly one: --source-parts or --remote-range-source")
    if args.mode == "verify" and (args.source_parts or args.remote_range_source):
        p.error("Verify requires neither archive source nor remote download")
    began = time.monotonic()
    original, _ = zip_member_directory(args.tail, args.part_sizes)
    paths, question_count, unique_questions = needed_paths(args.comparisons, args.clips)
    if (len(paths) != EXPECTED_REQUIRED_CLIPS
            or question_count != 533 or unique_questions != 346):
        raise ValueError("Dataset changed: fail closed instead of caching wrong audio")
    required = resolve_members(paths, original)
    result = (build(args.cache, required, args.source_parts, args.part_sizes,
                    remote_range_source=args.remote_range_source)
              if args.mode == "build" else verify(args.cache, required))
    result.update({
        "mode": args.mode,
        "wall_seconds": round(time.monotonic() - began, 3),
        "clip_package_schema": "mtt-1019-clips-stored-v1",
    })
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
