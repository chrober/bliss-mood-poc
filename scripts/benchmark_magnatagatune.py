#!/usr/bin/env python3
"""Bounded MagnaTagATune sparse-range AUDIO smoke and human-triplet benchmark.

Research-only; first run selects just four high-consensus development triplets.
Never downloads the full ~2.77-GiB split ZIP, never uploads licensed audio,
track identities, votes or vectors. Uses corrected pinned Rust-v5 features.
Human labels determine *which* development questions are sampled: these
scores must never be presented as unbiased test performance.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
import time
import zlib
import zipfile

import audit_magnatagatune_archive as directory
from audit_magnatagatune_votes import read_clips, dict_reader, COMPARISON_FIELDS
import evaluate_similarity as ev

BASE = "https://mirg.city.ac.uk/datasets/magnatagatune/"
MAX_MEMBER_COMPRESSED = 8 * 1024 * 1024
MAX_CLIP_RAW = 20 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def triplets_by_vote(comparisons: Path, clips: Path) -> tuple[dict, dict]:
    catalog, _ = read_clips(clips)
    votes_by_group = defaultdict(Counter)
    appearances = Counter()
    with comparisons.open("r", encoding="utf-8-sig", newline="") as file:
        for row in dict_reader(file, COMPARISON_FIELDS):
            ids = [row[f"clip{i}_id"].strip() for i in (1, 2, 3)]
            if len(set(ids)) != 3 or any(k not in catalog for k in ids):
                raise ValueError("Invalid MTT question clip IDs")
            group = tuple(sorted(ids))
            appearances[group] += 1
            for i, ident in enumerate(ids, 1):
                if row[f"clip{i}_mp3_path"].strip() != catalog[ident]["mp3_path"]:
                    raise ValueError("Mismatch between voted clip path and catalog")
                v = int(row[f"clip{i}_numvotes"])
                if v < 0:
                    raise ValueError("Negative human outlier votes")
                votes_by_group[group][ident] += v
    if not votes_by_group:
        raise ValueError("No voted triplets")
    return {
        triple: {"votes": dict(counts), "total": sum(counts.values()),
                 "permutations": appearances[triple]}
        for triple, counts in votes_by_group.items()
    }, catalog


def dev_selection(triplets: dict, catalog: dict, count: int, seed: int,
                  min_consensus: float = .7) -> list[tuple]:
    """Deterministic, artist-disjoint *development-smoke* selection.

    No test or final benchmark split is defined by this function.
    """
    if not 1 <= count <= 20:
        raise ValueError("Development smoke is capped at 20 triplets")
    valid = []
    for triple, data in triplets.items():
        votes = data["votes"]
        total = data["total"]
        if total <= 0:
            continue
        highest = max(votes.values())
        if sum(value == highest for value in votes.values()) != 1:
            continue
        if highest / total < min_consensus:
            continue
        artists = [catalog[clip]["artist"] for clip in triple]
        songs = [catalog[clip]["song_group"] for clip in triple]
        if any(not name for name in artists) or len(set(songs)) != 3:
            continue
        valid.append(triple)
    rng = random.Random(seed)
    valid.sort()
    rng.shuffle(valid)
    selected = []
    used_artists = set()
    for triple in valid:
        artists = {catalog[clip]["artist"] for clip in triple}
        if used_artists & artists:
            continue
        selected.append(triple)
        used_artists.update(artists)
        if len(selected) >= count:
            break
    if len(selected) != count:
        raise ValueError("Insufficient disjoint-artist high-consensus MTT triplets")
    return selected


def member_lookup(members: dict, path: str):
    canonical = directory.zip_path(path)
    if canonical in members:
        return members[canonical]
    matches = [info for filename, info in members.items()
               if filename.endswith("/" + canonical)]
    if len(matches) != 1:
        raise ValueError("MTT archive clip path missing or ambiguous")
    return matches[0]


class RangeFetcher:
    def __init__(self, part_sizes: list[int]):
        if len(part_sizes) != 3 or any(s < 1024 for s in part_sizes):
            raise ValueError("Invalid multipart archive sizes")
        self.part_sizes = part_sizes
        self.total_bytes = 0
        self.requests = 0

    def read(self, start: int, length: int) -> bytes:
        if length < 1 or length > MAX_MEMBER_COMPRESSED + 10000:
            raise ValueError("Requested sparse ZIP byte range too large")
        if start < 0 or start + length > sum(self.part_sizes):
            raise ValueError("Sparse archive range beyond declared ZIP size")
        pieces = []
        left = length
        cursor = start
        cumulative = 0
        for index, size in enumerate(self.part_sizes, 1):
            right = cumulative + size
            if cursor >= right:
                cumulative = right
                continue
            position = cursor - cumulative
            take = min(left, right - cursor)
            if take <= 0:
                cumulative = right
                continue
            pieces.append(self._part_range(index, position, position + take - 1))
            cursor += take
            left -= take
            cumulative = right
            if left == 0:
                break
        if left:
            raise ValueError("Unable to satisfy remote range")
        return b"".join(pieces)

    def _part_range(self, part: int, start: int, end: int) -> bytes:
        url = BASE + f"mp3.zip.{part:03d}"
        expected = end - start + 1
        # Each request is bounded to a single compressed MP3; never
        # permit an ignored Range to download a complete GB-sized part.
        with tempfile.TemporaryDirectory(prefix="mtt-range-") as temp:
            headers = Path(temp) / "headers.txt"
            body = Path(temp) / "data.bin"
            call = subprocess.run([
                "curl", "--fail", "--location", "--retry", "2",
                "--retry-all-errors", "--connect-timeout", "20",
                "--max-time", "180", "--max-filesize", str(expected + 10000),
                "--silent", "--show-error", "--header", "Accept-Encoding: identity",
                "--range", f"{start}-{end}",
                "--dump-header", str(headers),
                "--output", str(body), "--write-out", "%{http_code}", url
            ], capture_output=True, text=True, check=False, timeout=200)
            if call.returncode != 0 or call.stdout.strip() != "206":
                raise RuntimeError(
                    f"HTTP range download failed for MTT part {part}; "
                    f"code {call.returncode}; HTTP {call.stdout.strip()}"
                )
            metadata = headers.read_text(encoding="iso-8859-1")
            ranges = re.findall(
                r"(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$",
                metadata
            )
            if not ranges or tuple(map(int, ranges[-1][:2])) != (start, end):
                raise ValueError("Remote server returned incorrect Content-Range")
            if int(ranges[-1][2]) != self.part_sizes[part - 1]:
                raise ValueError("Remote ZIP part changed since metadata preflight")
            data = body.read_bytes()
            if len(data) != expected:
                raise ValueError("Truncated sparse MP3 byte range")
        self.total_bytes += expected
        self.requests += 1
        return data


def extract_mp3(info, source: RangeFetcher) -> bytes:
    """Retrieve and verify a ZIP member with 1-2 bounded range requests."""
    if (info.compress_size <= 0 or info.compress_size > MAX_MEMBER_COMPRESSED
            or info.file_size <= 0 or info.file_size > MAX_CLIP_RAW):
        raise ValueError("MTT MP3 ZIP member size out of safe research bounds")
    # Typical local extra fields are short. A modest slack avoids two HTTP
    # round-trips per clip. If larger, issue a second bounded range read.
    slack = min(1024, sum(source.part_sizes) - info.header_offset
                - info.compress_size - 30)
    span = 30 + info.compress_size + max(0, slack)
    packed = source.read(info.header_offset, span)
    header = struct.unpack("<IHHHHHIIIHH", packed[:30])
    if header[0] != 0x04034B50:
        raise ValueError("Remote ZIP member does not start with local file header")
    name_length, extra_length = header[-2:]
    start = 30 + name_length + extra_length
    needed = start + info.compress_size
    if needed > len(packed):
        packed += source.read(info.header_offset + len(packed),
                              needed - len(packed))
    local_name = packed[30:30 + name_length]
    expected = info.filename.encode(
        "utf-8" if info.flag_bits & 0x800 else "cp437"
    )
    if local_name != expected:
        raise ValueError("MP3 ZIP local member name differs from central directory")
    compressed = packed[start:needed]
    if info.compress_type == zipfile.ZIP_STORED:
        audio = compressed
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        decoder = zlib.decompressobj(-15)
        audio = decoder.decompress(compressed, MAX_CLIP_RAW + 1)
        audio += decoder.flush()
    else:
        raise ValueError("Unsupported archive ZIP compression method")
    if len(audio) != info.file_size or zlib.crc32(audio) != info.CRC:
        raise ValueError("Sparse MP3 CRC/length check failed")
    return audio


def run_inference(binary: Path, models_dir: Path, db: Path, selected: list,
                  clips: dict, members: dict, getter: RangeFetcher) -> dict:
    if db.exists():
        raise FileExistsError("Refuse to overwrite benchmark SQLite")
    db.parent.mkdir(parents=True, exist_ok=True)
    unique_ids = sorted({ident for triple in selected for ident in triple})
    start = time.monotonic()
    for position, ident in enumerate(unique_ids, 1):
        info = member_lookup(members, clips[ident]["mp3_path"])
        audio = extract_mp3(info, getter)
        with tempfile.TemporaryDirectory(prefix="mtt-single-mp3-") as temp:
            local = Path(temp) / "clip.mp3"
            local.write_bytes(audio)
            cmd = [
                str(binary.resolve()), "analyze-features", str(local),
                "--models-dir", str(models_dir.resolve()),
                "--models", "genre,moodtheme", "--threads", "1",
                "--db", str(db.resolve()), "--track-key", f"MTT/{ident}.mp3"
            ]
            completed = subprocess.run(
                cmd, check=False, text=True, capture_output=True, timeout=900
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"MTT inference failed on selected item {position}/{len(unique_ids)}: "
                    f"{completed.stderr[-1500:]}"
                )
        print(f"MTT analyzed clip {position}/{len(unique_ids)}", flush=True)
    return {
        "clips_analyzed": len(unique_ids),
        "analyze_and_sparse_download_wall_seconds": round(time.monotonic()-start, 3),
        "http_range_requests": getter.requests,
        "downloaded_audio_zip_bytes": getter.total_bytes,
        "workers": 1,
        "onnx_threads_per_song": 1,
    }


def evaluate(db: Path, selected: list, triplets: dict) -> dict:
    keys = {ident: f"MTT/{ident}.mp3"
            for group in selected for ident in group}
    with closing(ev.open_database(db)) as connection:
        cohort = {h: ev._catalog(connection, h, experimental=True)
                  for h in ev.MODELS}
        for head in ev.MODELS:
            if cohort[head]["preprocessing_version"] != (
                "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
            ):
                raise ValueError("MTT benchmark requires real corrected Rust-v5")
        vectors = ev.fetch_keys(connection, set(keys.values()), cohort)
        for ident in keys:
            if set(vectors[keys[ident]]) != set(ev.MODELS):
                raise ValueError("Missing complete MTT audio features")
        report = {}
        for head in ev.MODELS:
            scores = {}
            for name, fn in ev.METRIC_FUNCS.items():
                correct, pred, abstain = 0, 0, 0
                weighted_votes, eligible_votes = 0, 0
                for triple in selected:
                    a, b, c = triple
                    pair_scores = [
                        fn(vectors[keys[x]][head], vectors[keys[y]][head])
                        for x, y in ((a, b), (a, c), (b, c))
                    ]
                    if any(s is None or not math.isfinite(s) for s in pair_scores):
                        abstain += 1
                        continue
                    best = max(pair_scores)
                    # No meaningful overlap, no unique closest pair.
                    if (len([v for v in pair_scores if abs(best-v) <= 1e-12]) != 1
                            or (name.startswith("topk") and best <= 0)):
                        abstain += 1
                        continue
                    prediction = (c, b, a)[pair_scores.index(best)]
                    votes = triplets[triple]["votes"]
                    winner = max(votes, key=votes.get)
                    if sum(v == votes[winner] for v in votes.values()) != 1:
                        abstain += 1
                        continue
                    pred += 1
                    correct += int(prediction == winner)
                    weighted_votes += votes.get(prediction, 0)
                    eligible_votes += triplets[triple]["total"]
                scores[name] = {
                    "evaluated_questions": pred,
                    "abstained_questions": abstain,
                    "majority_odd_one_out_accuracy": correct / pred if pred else None,
                    "human_vote_weighted_agreement": weighted_votes / eligible_votes
                    if eligible_votes else None,
                }
            report[head] = {
                "model_key": cohort[head]["model_key"],
                "preprocessing_version": cohort[head]["preprocessing_version"],
                "metrics": scores,
            }
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("comparisons", "clips", "tail", "binary", "models-dir",
                 "db", "report"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--part-sizes", type=int, nargs=3, required=True)
    p.add_argument("--development-triplets", type=int, default=4)
    p.add_argument("--seed", type=int, default=20261021)
    args = p.parse_args()
    if args.db.exists() or args.report.exists():
        p.error("Refuse to overwrite old feature sidecar or results")
    for path in (args.comparisons, args.clips, args.tail, args.binary):
        if not path.is_file():
            p.error(f"Missing required input {path}")
    if not args.models_dir.is_dir():
        p.error("Models directory missing")
    triplets, clips = triplets_by_vote(args.comparisons, args.clips)
    selected = dev_selection(triplets, clips, args.development_triplets, args.seed)
    members, zipinfo = directory.zip_member_directory(args.tail, args.part_sizes)
    for ident in {c for triple in selected for c in triple}:
        member_lookup(members, clips[ident]["mp3_path"])
    fetcher = RangeFetcher(args.part_sizes)
    start = time.monotonic()
    diagnostic = run_inference(args.binary, args.models_dir, args.db,
                               selected, clips, members, fetcher)
    score_begin = time.monotonic()
    results = evaluate(args.db, selected, triplets)
    result = {
        "schema": "magnatagatune-odd-one-out-development-smoke-v1",
        "status": "research_smoke_only_not_a_holdout_or_metric_selection",
        "source": "https://mirg.city.ac.uk/datasets/magnatagatune/",
        "triplets_scored": len(selected),
        "unique_clip_ids": len({x for triple in selected for x in triple}),
        "seed": args.seed, "selection_consensus_minimum": 0.7,
        "sampling_policy": "high_consensus_disjoint_artist_dev_only",
        "selection_sha256": hashlib.sha256(
            "\n".join(",".join(t) for t in selected).encode("utf8")
        ).hexdigest(),
        "inputs": {"comparisons_sha256": digest(args.comparisons),
                   "clip_info_sha256": digest(args.clips),
                   "archive_directory_tail_sha256": digest(args.tail)},
        "archive": zipinfo,
        "resource_stats": {**diagnostic,
                           "end_to_end_audio_score_wall_seconds":
                               round(time.monotonic()-start, 3),
                           "score_wall_seconds":
                               round(time.monotonic()-score_begin, 3)},
        "per_head": results,
        "limitations": [
            "Tiny 4-triplet high-consensus DEVELOPMENT SMOKE, not final performance.",
            "Selection uses human labels to choose clear examples; this is not a random holdout.",
            "Original corpus includes 533 ordered rows but fewer unique unordered triplets.",
            "All clip audio temporary; only grouped aggregate metrics published.",
            "Human voting represents general perceived similarity, not Genre/Mood ground truth.",
            "Model training overlap not independently verified; no production metric is chosen.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": result["status"], "triplets": len(selected),
        "resource_stats": result["resource_stats"],
        "mood_cosine": results["moodtheme"]["metrics"]["cosine"],
    }, indent=2))


if __name__ == "__main__":
    main()
