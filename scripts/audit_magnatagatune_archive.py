#!/usr/bin/env python3
"""Inspect a multipart ZIP's *central directory* from a bounded tail only.

The official MagnaTagATune mp3.zip.001/.002/.003 are consecutive byte ranges
of ONE large ZIP. The central directory lives at the end of part .003.
The supplied tail is the last N bytes of that third part (HTTP Range 206).
No full ZIP, audio decode, public clip paths, track IDs, or scores involved.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import time
import zipfile

from audit_magnatagatune_votes import (
    read_clips, dict_reader, COMPARISON_FIELDS,
)


class RemoteZipTail(io.RawIOBase):
    """Virtual seekable ZIP; only bounded final bytes exist in the local file."""

    def __init__(self, tail_path: Path, total_size: int):
        self.source = tail_path.open("rb")
        self.size = total_size
        self.start = total_size - tail_path.stat().st_size
        if self.start < 0:
            raise ValueError("Tail exceeds virtual ZIP size")
        self.position = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_CUR:
            offset += self.position
        elif whence == io.SEEK_END:
            offset += self.size
        elif whence != io.SEEK_SET:
            raise ValueError("Invalid seek origin")
        if offset < 0 or offset > self.size:
            raise ValueError("ZIP central directory outside file")
        self.position = offset
        return offset

    def read(self, amount: int = -1) -> bytes:
        if self.position < self.start:
            raise ValueError(
                "ZIP directory not inside bounded tail; increase suffix range"
            )
        remaining = self.size - self.position
        if amount is None or amount < 0:
            amount = remaining
        amount = min(remaining, amount)
        self.source.seek(self.position - self.start)
        output = self.source.read(amount)
        self.position += len(output)
        return output

    def close(self):
        if not self.closed:
            self.source.close()
        super().close()


def zip_path(value: str) -> str:
    raw = value.replace("\\", "/")
    if raw.startswith("/") or ".." in raw.split("/"):
        raise ValueError("Invalid relative clip archive path")
    name = raw
    while name.startswith("./"):
        name = name[2:]
    sections = PurePosixPath(name).parts
    if not sections or sections == (".",):
        raise ValueError("Invalid relative clip archive path")
    return "/".join(sections)


def zip_member_directory(tail_path: Path, sizes: list[int]) -> tuple[dict, dict]:
    if len(sizes) != 3 or any(s <= 0 for s in sizes):
        raise ValueError("Require three positive multipart ZIP file sizes")
    total = sum(sizes)
    if tail_path.stat().st_size > sizes[2]:
        raise ValueError("Tail larger than last archive part")
    reader = RemoteZipTail(tail_path, total)
    try:
        with zipfile.ZipFile(reader) as archive:
            members = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = zip_path(info.filename)
                if name in members:
                    raise ValueError("Duplicate ZIP entry path")
                members[name] = info
    finally:
        reader.close()
    if len(members) < 100:
        raise ValueError("Archive central directory has implausibly few entries")
    return members, {
        "archive_data_parts": 3,
        "part_byte_lengths": sizes,
        "combined_zip_bytes": total,
        "bounded_tail_bytes": tail_path.stat().st_size,
        "zip_nondirectory_entries": len(members),
    }


def needed_paths(comparisons: Path, clipinfo: Path) -> tuple[set[str], int, int]:
    catalog, _ = read_clips(clipinfo)
    required = {}
    unordered = set()
    question_count = 0
    with comparisons.open("r", encoding="utf-8-sig", newline="") as src:
        for row in dict_reader(src, COMPARISON_FIELDS):
            question_count += 1
            ids = [row[f"clip{i}_id"].strip() for i in (1, 2, 3)]
            if len(set(ids)) != 3 or any(k not in catalog for k in ids):
                raise ValueError("Missing or duplicate clip reference in vote triplet")
            unordered.add(tuple(sorted(ids)))
            for i, clip_id in enumerate(ids, 1):
                meta = catalog[clip_id]
                from_votes = row[f"clip{i}_mp3_path"].strip()
                if from_votes != meta["mp3_path"] or not from_votes:
                    raise ValueError("Vote audio path differs from clip catalog")
                canonical = zip_path(from_votes)
                if clip_id in required and required[clip_id] != canonical:
                    raise ValueError("Clip ID maps to multiple MP3 paths")
                required[clip_id] = canonical
    if len(set(required.values())) != len(required):
        raise ValueError("Distinct referenced clip IDs alias the same audio path")
    return set(required.values()), question_count, len(unordered)


def evaluate(tail: Path, sizes: list[int], comparisons: Path, clips: Path) -> dict:
    start = time.monotonic()
    members, zipstat = zip_member_directory(tail, sizes)
    paths, questions, unordered = needed_paths(comparisons, clips)
    # Full and path-suffix matching are both counted. A suffix is accepted
    # only when it is unique in the archive's central directory.
    suffixes = defaultdict(set)
    for name in members:
        fragments = name.split("/")
        for i in range(len(fragments)):
            suffixes["/".join(fragments[i:])].add(name)
    exact = 0
    suffix_only = 0
    missing = 0
    ambiguous = 0
    resolved = set()
    approximate_parts = Counter()
    compressed_sum = 0
    boundaries = [sizes[0], sizes[0] + sizes[1]]
    for path in paths:
        candidates = {path} if path in members else suffixes.get(path, set())
        if not candidates:
            missing += 1
            continue
        if len(candidates) != 1:
            ambiguous += 1
            continue
        actual = next(iter(candidates))
        if actual != path:
            suffix_only += 1
        else:
            exact += 1
        resolved.add(actual)
        info = members[actual]
        compressed_sum += info.compress_size
        # Count where local file header starts. Header and data can span
        # multipart boundaries; offsets alone are not download partitions.
        index = 0 if info.header_offset < boundaries[0] else (
            1 if info.header_offset < boundaries[1] else 2
        )
        approximate_parts[f"part_{index+1}"] += 1
    return {
        "schema": "magnatagatune-multipart-zip-membership-v1",
        "status": "PASS_all_required_clip_paths_in_zip_central_directory"
        if not missing and not ambiguous else "BLOCKED_incomplete_archive_membership",
        "metadata_questions": questions,
        "unique_unordered_clip_triplets": unordered,
        "triplet_rows_with_permuted_or_repeated_clip_sets": questions - unordered,
        "required_unique_mp3s": len(paths),
        "audio_member_matches": {"exact": exact, "unique_path_suffix": suffix_only,
                                 "missing": missing, "ambiguous": ambiguous},
        "required_compressed_mp3_bytes": compressed_sum,
        "approx_member_local_header_start_part": dict(sorted(approximate_parts.items())),
        "zip": zipstat,
        "input_hashes": {
            "comparisons_sha256": _digest(comparisons),
            "clips_sha256": _digest(clips),
            "zip_tail_sha256": _digest(tail),
        },
        "runtime": {"audit_seconds": round(time.monotonic()-start, 3)},
        "limitations": [
            "HTTP Range suffix is read-only ZIP central-directory inspection; no audio downloaded.",
            "Directory listing does NOT verify compressed member payload integrity or decoding.",
            "Multipart files must be concatenated in .001/.002/.003 order to extract data.",
            "Approximate start-part is NOT proof a compressed entry occupies only that part.",
            "Repeated/permuted unordered triplets are not independent observations.",
            "No artist, clip identity, path, raw vote, human annotation or audio published.",
        ],
    }


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--last-part-tail", type=Path, required=True)
    p.add_argument("--part-sizes", type=int, nargs=3, required=True)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.report.exists():
        p.error("Report already exists; refuse overwrite")
    result = evaluate(args.last_part_tail, args.part_sizes,
                      args.comparisons, args.clips)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": result["status"],
        "zip_entries": result["zip"]["zip_nondirectory_entries"],
        "required_unique_mp3s": result["required_unique_mp3s"],
        "matches": result["audio_member_matches"],
        "unique_unordered_clip_triplets": result["unique_unordered_clip_triplets"],
        "compressed_needed_bytes": result["required_compressed_mp3_bytes"],
        "runtime": result["runtime"],
    }, indent=2))
    if result["status"] != "PASS_all_required_clip_paths_in_zip_central_directory":
        raise SystemExit("MTT archive membership is incomplete; no audio phase allowed")


if __name__ == "__main__":
    main()
