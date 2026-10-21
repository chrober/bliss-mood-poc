#!/usr/bin/env python3
"""Range-only membership preflight for the original MagnaTagATune split ZIP.

Retrieve ONLY the tail of mp3.zip.003 (at most 16 MiB). The three files are
parts of one ordinary ZIP byte stream, not three independent ZIP archives.
Parse its central directory without accessing MP3 payload bytes.

Fail closed if HTTP ranges are ignored, directory falls outside tail,
split-zip format differs, or clip names cannot be mapped unambiguously.
No individual source filenames or per-clip metadata are printed or stored.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import time
from urllib.request import Request, urlopen

from audit_magnatagatune_votes import CLIP_FIELDS, COMPARISON_FIELDS, dict_reader, read_clips

BASE = "https://mirg.city.ac.uk/datasets/magnatagatune/"
TAIL_BYTES = 16 * 1024 * 1024
EOCD = struct.Struct("<4s4H2LH")
CENTRAL = struct.Struct("<4s2B4HL2L5H2L")
CONTENT_RANGE = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$")


def source_hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def source_sizes(base: str = BASE) -> list[int]:
    sizes = []
    for part in ("001", "002", "003"):
        req = Request(base + "mp3.zip." + part,
                      headers={"Accept-Encoding": "identity"}, method="HEAD")
        with urlopen(req, timeout=90) as response:
            if response.status != 200:
                raise ValueError(f"Unexpected HTTP status on MTT shard HEAD: {response.status}")
            size = int(response.headers.get("Content-Length", "0"))
            if size < 100_000_000 or size > 1_500_000_000:
                raise ValueError("Unexpected MTT audio shard size")
            sizes.append(size)
    return sizes


def fetch_tail(sizes: list[int], base: str = BASE,
               max_bytes: int = TAIL_BYTES) -> tuple[bytes, int]:
    if len(sizes) != 3 or not 0 < max_bytes <= TAIL_BYTES:
        raise ValueError("Invalid MTT audio shard sizes or range budget")
    final_size = sizes[2]
    count = min(max_bytes, final_size)
    req = Request(
        base + "mp3.zip.003",
        headers={"Range": f"bytes={final_size-count}-{final_size-1}",
                 "Accept-Encoding": "identity"},
    )
    with urlopen(req, timeout=180) as response:
        if response.status != 206:
            # Do not read response body: server ignoring Range might send
            # 737 MiB despite a request for only 16 MiB.
            raise ValueError("Official MTT host did not honor HTTP byte ranges; audio download aborted")
        text = response.headers.get("Content-Range", "")
        match = CONTENT_RANGE.fullmatch(text.strip())
        if not match:
            raise ValueError("Invalid HTTP Content-Range from official MTT archive")
        start, stop, total = map(int, match.groups())
        if (start != final_size - count or stop != final_size-1 or
            total != final_size):
            raise ValueError("Server returned unexpected MTT shard range")
        data = response.read(count+1)
        if len(data) != count:
            raise ValueError("Partial/truncated or oversize response for MTT ZIP index")
    return data, sum(sizes)-len(data)


def directory_names(tail: bytes, global_tail_offset: int,
                    archive_size: int) -> tuple[set[str], dict]:
    """Read ZIP central directory with explicit offsets. No MP3 extraction."""
    position = tail.rfind(b"PK\x05\x06")
    if position < 0 or position + EOCD.size > len(tail):
        raise ValueError("ZIP end-of-central-directory missing in ranged archive tail")
    (signature, disk, directory_disk, disk_entries, total_entries,
     directory_size, directory_offset, comment_length) = EOCD.unpack_from(tail, position)
    if (signature != b"PK\x05\x06" or disk != 0 or directory_disk != 0 or
        disk_entries != total_entries or total_entries >= 65535 or
        directory_size >= 0xffffffff or directory_offset >= 0xffffffff):
        raise ValueError("Unexpected multi-disk or ZIP64 central directory; reject unsafe interpretation")
    if position + EOCD.size + comment_length != len(tail):
        raise ValueError("ZIP EOCD does not terminate archive")
    offset = directory_offset - global_tail_offset
    if offset < 0 or offset + directory_size != position:
        raise ValueError("ZIP central directory not fully available in bounded tail")
    if global_tail_offset + len(tail) != archive_size:
        raise ValueError("Untrusted or inconsistent MTT ZIP part sizes")
    names = set()
    directories = 0
    offset_end = offset + directory_size
    for _ in range(total_entries):
        if offset + CENTRAL.size > offset_end:
            raise ValueError("Truncated ZIP central record")
        record = CENTRAL.unpack_from(tail, offset)
        if record[0] != b"PK\x01\x02":
            raise ValueError("Corrupt ZIP central directory signature")
        flags = record[5]
        method = record[6]
        compressed = record[10]
        uncompressed = record[11]
        name_len, extra_len, comment_len = record[12], record[13], record[14]
        name_start = offset + CENTRAL.size
        offset = name_start + name_len + extra_len + comment_len
        if offset > offset_end:
            raise ValueError("ZIP central directory field overflow")
        encoded = tail[name_start:name_start+name_len]
        name = encoded.decode("utf-8" if flags & 0x800 else "cp437")
        if not name or name.startswith("/") or "\\" in name or ".." in PurePosixPath(name).parts:
            raise ValueError("Invalid or unsafe ZIP member name")
        if method not in (0, 8):
            raise ValueError("Unexpected ZIP compression method in MTT archive")
        if compressed >= 0xffffffff or uncompressed >= 0xffffffff:
            raise ValueError("ZIP64 per-entry size not supported by bounded preflight")
        if name in names:
            raise ValueError("Duplicate archive member path")
        names.add(name)
        directories += int(name.endswith("/"))
    if offset != offset_end:
        raise ValueError("Unexpected trailing ZIP central directory data")
    return names, {
        "archive_total_bytes": archive_size,
        "central_directory_bytes": directory_size,
        "zip_entries": len(names),
        "zip_directories": directories,
    }


def required_mp3_paths(comparisons: Path, clips_path: Path) -> set[str]:
    clips, _ = read_clips(clips_path)
    required = set()
    with comparisons.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = dict_reader(input_file, COMPARISON_FIELDS)
        for row in reader:
            if None in row:
                raise ValueError("Malformed MTT vote CSV")
            for i in (1, 2, 3):
                ident = row[f"clip{i}_id"].strip()
                if ident not in clips:
                    raise ValueError("MTT vote references unknown clip")
                expected = clips[ident]["mp3_path"]
                if not expected or expected != row[f"clip{i}_mp3_path"].strip():
                    raise ValueError("MTT clip path missing or disagrees with catalog")
                if (expected.startswith("/") or "\\" in expected or
                    ".." in PurePosixPath(expected).parts):
                    raise ValueError("Unsafe MTT reference MP3 path")
                required.add(expected)
    if not 100 <= len(required) <= 5000:
        raise ValueError("Unexpected count of MTT required clips")
    return required


def audit(required: set[str], archived: set[str], stats: dict) -> dict:
    # Only known prefixes are checked; no fuzzy basename or title matching.
    variants = {
        "exact": lambda p: p,
        "mp3_prefix": lambda p: "mp3/" + p,
    }
    counts = {}
    for name, variant in variants.items():
        counts[name] = sum(variant(p) in archived for p in required)
    matching = [name for name, count in counts.items() if count == len(required)]
    if len(matching) != 1:
        raise ValueError(
            f"No single unambiguous MTT archive path mapping: "
            f"required={len(required)}, exact={counts['exact']}, "
            f"mp3_prefix={counts['mp3_prefix']}"
        )
    # We do not export raw clip filenames, votes, artist or album records.
    return {
        "schema": "magnatagatune-zip-central-directory-preflight-v1",
        "status": "verified_metadata_to_archive_paths_NO_audio_decoding_or_training",
        "required_unique_clips": len(required),
        "members_covering_required_clips": len(required),
        "path_mapping": matching[0],
        **stats,
        "warnings": [
            "Archive listing is not proof that every MP3 payload decodes correctly.",
            "This is research-only membership evidence, not a numerical or musical similarity result.",
            "No raw MP3 data or per-track filenames are stored in the public report.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparisons", type=Path, required=True)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Refuse to overwrite research report")
    began = time.monotonic()
    sizes = source_sizes()
    tail, start = fetch_tail(sizes)
    names, directory = directory_names(tail, start, sum(sizes))
    required = required_mp3_paths(args.comparisons, args.clips)
    report = audit(required, names, directory)
    report["source"] = BASE
    report["shard_bytes"] = sizes
    report["range_tail_bytes_downloaded"] = len(tail)
    report["comparisons_sha256"] = source_hash(args.comparisons)
    report["clip_metadata_sha256"] = source_hash(args.clips)
    report["runtime_wall_seconds"] = round(time.monotonic()-began, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as dest:
        json.dump(report, dest, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": report["status"],
        "required_unique_clips": report["required_unique_clips"],
        "total_archive_members": report["zip_entries"],
        "path_mapping": report["path_mapping"],
        "ranged_bytes": report["range_tail_bytes_downloaded"],
        "seconds": report["runtime_wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
