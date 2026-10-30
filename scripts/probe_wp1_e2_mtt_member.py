#!/usr/bin/env python3
"""WP1-E2: verify exactly ONE registered MTT clip against source ZIP CRC.

Research-only diagnostic, no audio/model inference, no audio output/archive.
Inputs are official metadata, an 8-MiB central-directory tail and 3 validated
part lengths. Full MTT coverage and musical quality MUST NOT be inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import benchmark_magnatagatune as mtt
from audit_magnatagatune_archive import zip_member_directory, needed_paths
from mtt_selected_clip_cache import resolve_members

SCHEMA = "wp1-e2-mtt-one-registered-clip-diagnostic-v1"
MAX_TAIL = 8_388_608


def check_one(tail: Path, sizes: list[int], comparisons: Path,
              clips: Path) -> dict:
    if len(sizes) != 3 or not all(500_000_000 < n < 1_500_000_000 for n in sizes):
        raise ValueError("Invalid official archive part sizes")
    if not tail.is_file() or tail.stat().st_size != MAX_TAIL:
        raise ValueError("Official central-directory tail missing or not bounded")
    if mtt.digest(comparisons) != mtt.REGISTERED_MTT_COMPARISONS_SHA256:
        raise ValueError("Original MTT comparisons provenance mismatch")
    if mtt.digest(clips) != mtt.REGISTERED_MTT_CLIPS_SHA256:
        raise ValueError("Original MTT clip metadata provenance mismatch")
    members, _ = zip_member_directory(tail, sizes)
    paths, question_count, unique_questions = needed_paths(comparisons, clips)
    if len(paths) != 1019 or question_count != 533 or unique_questions != 346:
        raise ValueError("Unexpected official 1019-clip research membership")
    required = resolve_members(paths, members)
    # Stable deterministic selection; never report the private/public path or ID.
    selected_path = min(required, key=lambda name: hashlib.sha256(
        name.encode("utf-8")).hexdigest())
    from benchmark_magnatagatune import RangeFetcher, extract_mp3
    source = RangeFetcher(sizes)
    audio = extract_mp3(required[selected_path], source)
    return {
        "schema": SCHEMA,
        "status": "ONE_OFFICIAL_MEMBER_RANGE_AND_ZIP_CRC_PASS",
        "official_comparisons_verified": True,
        "official_clip_metadata_verified": True,
        "required_clips_in_official_directory": 1019,
        "source_part_count": 3,
        "tested_clips": 1,
        "fetched_bytes": source.total_bytes,
        "range_requests": source.requests,
        "decoded_clip_crc_verified": True,
        "clip_bytes_processed_in_memory_only": len(audio),
        "all_1019_clips_accessible_proven": False,
        "global_pairwise_fusion_measured": False,
        "song_keys_or_audio_in_report": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail", required=True, type=Path)
    parser.add_argument("--part-sizes", required=True, nargs=3, type=int)
    parser.add_argument("--comparisons", required=True, type=Path)
    parser.add_argument("--clips", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        parser.error("Refuse to overwrite diagnostic report")
    try:
        result = check_one(args.tail, args.part_sizes,
                           args.comparisons, args.clips)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        # Never output selected ZIP-member names or paths from any exception.
        status = ("RANGE_TRANSPORT_BLOCKED" if isinstance(exc, RuntimeError)
                  else "METADATA_OR_CRC_PROVENANCE_BLOCKED")
        result = {
            "schema": SCHEMA,
            "status": status,
            "tested_clips": 0,
            "all_1019_clips_accessible_proven": False,
            "global_pairwise_fusion_measured": False,
            "song_keys_or_audio_in_report": False,
        }
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
