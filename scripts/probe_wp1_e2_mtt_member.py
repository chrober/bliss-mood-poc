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



def check_sample(tail: Path, sizes: list[int], comparisons: Path,
                 clips: Path, per_part: int = 10) -> dict:
    """Fixed SHA256 selection of 10 different registered clips per ZIP part.

    No candidate is chosen by its acoustic score or prior benchmark output.
    RangeFetcher itself enforces 3.5-second pacing, exact HTTP 206 ranges
    and bounded payload sizes. Stop on first failure; disclose counts only.
    """
    if type(per_part) is not int or per_part < 1 or per_part > 10:
        raise ValueError("Out-of-bounds sample size")
    if len(sizes) != 3 or not all(500_000_000 < n < 1_500_000_000 for n in sizes):
        raise ValueError("Invalid multipart archive sizes")
    if not tail.is_file() or tail.stat().st_size != MAX_TAIL:
        raise ValueError("Official ZIP directory tail absent or unbounded")
    if mtt.digest(comparisons) != mtt.REGISTERED_MTT_COMPARISONS_SHA256:
        raise ValueError("MTT official comparisons changed")
    if mtt.digest(clips) != mtt.REGISTERED_MTT_CLIPS_SHA256:
        raise ValueError("MTT official clip catalog changed")
    members, _ = zip_member_directory(tail, sizes)
    paths, question_count, unique_questions = needed_paths(comparisons, clips)
    if len(paths) != 1019 or question_count != 533 or unique_questions != 346:
        raise ValueError("Required MTT clip/question set changed")
    required = resolve_members(paths, members)
    boundaries = [sizes[0], sizes[0] + sizes[1], sum(sizes)]
    from benchmark_magnatagatune import RangeFetcher, extract_mp3
    by_part = {1: [], 2: [], 3: []}
    for name, info in required.items():
        offset = info.header_offset
        if not isinstance(offset, int) or offset < 0 or offset >= boundaries[-1]:
            raise ValueError("ZIP entry offset outside archive")
        part = 1 if offset < boundaries[0] else 2 if offset < boundaries[1] else 3
        by_part[part].append((hashlib.sha256(name.encode("utf-8")).digest(),
                              name, info))
    if any(len(choices) < per_part for choices in by_part.values()):
        raise ValueError("Not enough official registered clips in each ZIP part")
    # Interleave source parts, not all one part first.
    selections = {part: sorted(by_part[part], key=lambda row: row[0])[:per_part]
                  for part in (1, 2, 3)}
    source = RangeFetcher(sizes)
    verified = {1: 0, 2: 0, 3: 0}
    status = "BOUNDED_MULTIPART_MEMBER_CRC_SAMPLE_PASS"
    failure_kind = None
    for i in range(per_part):
        for part in (1, 2, 3):
            _, _, info = selections[part][i]
            try:
                audio = extract_mp3(info, source)
                if not audio:
                    raise ValueError("Empty decoded MP3")
            except RuntimeError:
                status, failure_kind = "SAMPLE_STOPPED", "RANGE_TRANSPORT_FAILURE"
                break
            except (ValueError, OSError):
                status, failure_kind = "SAMPLE_STOPPED", "ZIP_MEMBER_OR_CRC_FAILURE"
                break
            verified[part] += 1
        if status == "SAMPLE_STOPPED":
            break
    return {
        "schema": "wp1-e2-mtt-bounded-30-clip-crc-sample-v1",
        "status": status,
        "requested_clips": 3 * per_part,
        "verified_clips": sum(verified.values()),
        "per_archive_part_verified_counts": {
            "part_001": verified[1],
            "part_002": verified[2],
            "part_003": verified[3],
        },
        "failure_kind": failure_kind,
        "range_requests": source.requests,
        "fetched_bytes": source.total_bytes,
        "source_rate_limited_to_3_5_seconds_between_requests": True,
        "all_1019_clips_accessible_proven": False,
        "global_pairwise_fusion_measured": False,
        "audio_or_track_ids_in_report": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tail", required=True, type=Path)
    parser.add_argument("--part-sizes", required=True, nargs=3, type=int)
    parser.add_argument("--comparisons", required=True, type=Path)
    parser.add_argument("--clips", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-per-part", type=int, default=0,
                        help="1..10 fixed CRC-verified clips per each of 3 source parts")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        parser.error("Refuse to overwrite diagnostic report")
    try:
        if args.sample_per_part:
            result = check_sample(args.tail, args.part_sizes,
                                  args.comparisons, args.clips,
                                  per_part=args.sample_per_part)
        else:
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
