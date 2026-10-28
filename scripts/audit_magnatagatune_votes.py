#!/usr/bin/env python3
"""Schema-specific metadata-only MagnaTagATune odd-one-out vote audit.

Based on the official 2026-10-21 preflight: comparisons_final.csv has 3
clip IDs, 3 vote counts, 3 MP3 path columns; clip_info_final.csv has
clip_id, title, artist, album, track_number, mp3_path, etc. Inspect
agreement and identity coverage without downloading any audio or
exporting any individual clip/artist/path or raw judgement.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
import time

COMPARISON_FIELDS = [
    "clip1_id", "clip2_id", "clip3_id",
    "clip1_numvotes", "clip2_numvotes", "clip3_numvotes",
    "clip1_mp3_path", "clip2_mp3_path", "clip3_mp3_path",
]
CLIP_FIELDS = [
    "clip_id", "track_number", "title", "artist", "album",
    "url", "segmentStart", "segmentEnd", "original_url", "mp3_path",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dict_reader(source, expected: list[str]):
    """Use official CSV's real delimiter; preserve exact required columns."""
    sample = source.read(4096)
    source.seek(0)
    try:
        separator = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        separator = ","
    reader = csv.DictReader(source, delimiter=separator)
    if (not reader.fieldnames or len(reader.fieldnames) != len(expected)
            or set(reader.fieldnames) != set(expected)):
        raise ValueError("Unexpected official MTT CSV schema or delimiter")
    return reader


def read_clips(path: Path) -> tuple[dict, dict]:
    clips = {}
    missing_path = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = dict_reader(handle, CLIP_FIELDS)
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ValueError("Malformed MTT clip metadata row")
            ident = row["clip_id"].strip()
            if not ident or ident in clips:
                raise ValueError("Missing or duplicate MTT clip_id")
            path_value = row["mp3_path"].strip()
            if not path_value:
                missing_path += 1
            clips[ident] = {
                "mp3_path": path_value,
                "song_group": tuple(row[k].strip().casefold()
                                    for k in ("artist","album","title","track_number")),
                "artist": row["artist"].strip().casefold(),
                "album": row["album"].strip().casefold(),
            }
    return clips, {"clip_metadata_rows": len(clips),
                   "clip_metadata_missing_audio_paths": missing_path}


def evaluate(comparisons: Path, clipinfo: Path) -> dict:
    start = time.monotonic()
    clips, clip_meta = read_clips(clipinfo)
    count = 0
    total_votes = 0
    strong = strict_majority = tied = unanimous = zero_votes = 0
    majority_oracle_votes = 0
    required_clip_ids = set()
    used_paths = set()
    groups = set()
    artists = set()
    albums = set()
    same_song = same_album = same_artist = 0
    vote_buckets = Counter()
    consensus_buckets = Counter()
    inconsistent_paths = 0
    with comparisons.open("r", encoding="utf-8-sig", newline="") as source:
        reader = dict_reader(source, COMPARISON_FIELDS)
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ValueError("Malformed MTT comparison metadata row")
            count += 1
            ids = [row[f"clip{i}_id"].strip() for i in (1, 2, 3)]
            if len(set(ids)) != 3 or any(key not in clips for key in ids):
                raise ValueError("Comparison has duplicate/missing clip metadata reference")
            votes = []
            for i in (1, 2, 3):
                raw = row[f"clip{i}_numvotes"].strip()
                try:
                    v = int(raw)
                except ValueError as e:
                    raise ValueError("Invalid MTT odd-one-out vote count") from e
                if v < 0:
                    raise ValueError("Negative odd-one-out votes")
                votes.append(v)
                key = ids[i - 1]
                clip = clips[key]
                given_path = row[f"clip{i}_mp3_path"].strip()
                if clip["mp3_path"] != given_path:
                    inconsistent_paths += 1
                required_clip_ids.add(key)
                if clip["mp3_path"]:
                    used_paths.add(clip["mp3_path"])
                groups.add(clip["song_group"])
                artists.add(clip["artist"])
                albums.add((clip["artist"], clip["album"]))
            triple_groups = [clips[k]["song_group"] for k in ids]
            triple_artists = [clips[k]["artist"] for k in ids]
            triple_albums = [(clips[k]["artist"], clips[k]["album"]) for k in ids]
            same_song += int(len(set(triple_groups)) < 3)
            same_artist += int(len(set(triple_artists)) < 3)
            same_album += int(len(set(triple_albums)) < 3)
            n = sum(votes)
            vote_buckets["0" if n == 0 else
                         "1-2" if n < 3 else
                         "3-9" if n < 10 else
                         "10-19" if n < 20 else "20+"] += 1
            total_votes += n
            if n == 0:
                zero_votes += 1
                continue
            maximum = max(votes)
            majority_oracle_votes += maximum
            winners = sum(v == maximum for v in votes)
            tied += int(winners > 1)
            strict_majority += int(maximum * 2 > n)
            unanimous += int(maximum == n)
            strong += int(winners == 1 and maximum / n >= .7)
            fraction = maximum / n
            consensus_buckets["<50%" if fraction < .5 else
                              "50-<70%" if fraction < .7 else
                              "70-<90%" if fraction < .9 else "90-100%"] += 1
    if count < 400 or not required_clip_ids:
        raise ValueError("Too few real MTT comparisons")
    if inconsistent_paths:
        raise ValueError(f"{inconsistent_paths} comparison clip MP3 paths mismatch catalog")
    if zero_votes > count // 5:
        raise ValueError("Too many MTT comparisons without human votes")
    return {
        "schema": "magnatagatune-human-triplet-vote-audit-v1",
        "source": "https://mirg.city.ac.uk/datasets/magnatagatune/",
        "status": "metadata_and_vote_preflight_no_audio_inference",
        "questions": count,
        "total_human_votes": total_votes,
        "votes_per_question_mean": total_votes / count,
        "votes_per_question_median": None,  # No raw votes exported.
        "question_vote_count_buckets": dict(sorted(vote_buckets.items())),
        "majority_vote": {
            "questions_with_no_votes": zero_votes,
            "questions_with_tied_top_votes": tied,
            "questions_with_strict_absolute_majority": strict_majority,
            "questions_unanimous": unanimous,
            "questions_with_unique_ge_70pct_consensus": strong,
            "fraction_of_votes_for_each_question_majority_choice":
                majority_oracle_votes / total_votes if total_votes else None,
            "consensus_buckets": dict(sorted(consensus_buckets.items())),
        },
        "audio_requirements": {
            "distinct_clip_ids_in_questions": len(required_clip_ids),
            "distinct_available_mp3_paths_in_questions": len(used_paths),
            "distinct_song_groups": len(groups),
            "distinct_artist_strings": len(artists),
            "distinct_artist_album_groups": len(albums),
            "questions_with_two_clips_same_original_song_group": same_song,
            "questions_with_two_clips_same_album": same_album,
            "questions_with_two_clips_same_artist": same_artist,
            **clip_meta,
        },
        "hashes": {"comparisons_sha256": sha(comparisons),
                   "clip_metadata_sha256": sha(clipinfo),
                   "required_clip_id_set_sha256": hashlib.sha256(
                       "\n".join(sorted(required_clip_ids)).encode("utf-8")
                   ).hexdigest()},
        "runtime": {"wall_seconds": round(time.monotonic() - start, 3)},
        "limitations": [
            "Human odd-one-out majority choices, not separate Genre or Mood labels.",
            "The maximum vote count in a triple is a human agreement ceiling, not measured algorithm accuracy.",
            "Clip catalog metadata may include more entries than available archive audio.",
            "Artist, album, title and track number are grouping proxies, not acoustical fingerprints.",
            "Consensus strength, ties, near-duplicate songs and original audio licensing require explicit treatment before evaluation.",
            "Neither input audio nor individual human records, clip paths, identities or votes are published.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparisons", type=Path, required=True)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Never overwrite a research report")
    report = evaluate(args.comparisons, args.clips)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "questions": report["questions"],
        "total_human_votes": report["total_human_votes"],
        "majority_vote": report["majority_vote"],
        "audio_requirements": report["audio_requirements"],
        "wall_seconds": report["runtime"]["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
