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
from mtt_local_archive import LocalMultipartRanges
from mtt_parallel_workers import analyze_parallel

BASE = "https://mirg.city.ac.uk/datasets/magnatagatune/"
# Frozen from metadata-only run 39592331265, artifact 12342707931;
# pin both the source CSVs and the artist-fold membership.
REGISTERED_MTT_COMPARISONS_SHA256 = "cf210e087ed5b3f3f8b164626e1d2857cf0ba9ae66bd9229bafe042889107a98"
REGISTERED_MTT_CLIPS_SHA256 = "cb6108a10d3a91f0bfd7d2fbec2382559d15f20c8d28093f14e12162a47a3e78"
REGISTERED_MTT_DEVELOPMENT_SHA256 = "1b7e74bfd7f17c3ef6646f65a07d68ce86be1018ea1a87ff3c922875f4a1b28e"
REGISTERED_MTT_HOLDOUT_SHA256 = "171f4c1da9cde13ce1a5ebabe27e40c3098ea69549193c6aa8c9942196d681ea"
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



def frozen_artist_development_selection(triplets: dict, catalog: dict) -> tuple[list, dict]:
    """Select only all-development artist triplets from the frozen 128/256 split.

    No model results influence this selection. The 56 holdout candidates
    are never sent to the remote audio fetcher or feature evaluator.
    """
    import audit_magnatagatune_holdout as holdout
    audit = holdout.evaluate_inputs(triplets, catalog)
    expected = audit["artist_disjoint_questions"]["development"]
    selected = sorted(
        triple for triple in triplets
        if all(holdout.artist_bucket(catalog[ident]["artist"], 128) == "development"
               for ident in triple)
    )
    if not selected or len(selected) != expected["count"]:
        raise ValueError("Frozen MTT development partition cardinality mismatch")
    if holdout.digest_triplets(selected) != expected["sorted_triplet_id_sha256"]:
        raise ValueError("Frozen MTT development partition fingerprint mismatch")
    excluded = set(triplets) - set(selected)
    if any(triple in excluded for triple in selected):
        raise ValueError("Frozen MTT selection collision")
    return selected, {
        "artist_hash_cutoff": 128,
        "policy": audit["artist_hash_policy"],
        "development_triplets": len(selected),
        "holdout_triplets_never_scored": audit["artist_disjoint_questions"]["holdout"]["count"],
        "mixed_triplets_excluded": audit["artist_disjoint_questions"]["mixed_excluded"]["count"],
        "development_partition_sha256": expected["sorted_triplet_id_sha256"],
        "holdout_partition_sha256":
            audit["artist_disjoint_questions"]["holdout"]["sorted_triplet_id_sha256"],
    }


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
        # Public archive server timed out after ~21-25 rapid GETs in two
        # otherwise successful GH runs. Cap request rate conservatively.
        self.min_request_spacing_seconds = 3.5
        self.next_request_at = 0.0
        self.range_pacing_sleep_seconds = 0.0

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
        wait_seconds = self.next_request_at - time.monotonic()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
            self.range_pacing_sleep_seconds += wait_seconds
        self.next_request_at = time.monotonic() + self.min_request_spacing_seconds
        # Each request is bounded to a single compressed MP3; never
        # permit an ignored Range to download a complete GB-sized part.
        with tempfile.TemporaryDirectory(prefix="mtt-range-") as temp:
            headers = Path(temp) / "headers.txt"
            body = Path(temp) / "data.bin"
            call = subprocess.run([
                # A 92-clip development run observed a transient curl 28
                # timeout after 21 successful clips; retry only bounded
                # Range requests, never whole multi-gigabyte ZIP parts.
                "curl", "--fail", "--location", "--retry", "5",
                "--retry-all-errors", "--retry-delay", "8",
                "--retry-max-time", "360", "--connect-timeout", "15",
                "--max-time", "50", "--max-filesize", str(expected + 10000),
                "--silent", "--show-error", "--header", "Accept-Encoding: identity",
                "--range", f"{start}-{end}",
                "--dump-header", str(headers),
                "--output", str(body), "--write-out", "%{http_code}", url
            ], capture_output=True, text=True, check=False, timeout=390)
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
        "http_request_min_spacing_s": getter.min_request_spacing_seconds,
        "http_range_pacing_sleep_seconds":
            round(getter.range_pacing_sleep_seconds, 3),
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
                correct, pred = 0, 0
                undefined, metric_ties, zero_overlap, human_ties = 0, 0, 0, 0
                weighted_votes, eligible_votes = 0, 0
                consensus = {"under_70pct": [0, 0], "at_least_70pct": [0, 0]}
                for triple in selected:
                    a, b, c = triple
                    votes = triplets[triple]["votes"]
                    majority_count = max(votes.values())
                    if sum(v == majority_count for v in votes.values()) != 1:
                        human_ties += 1
                        continue
                    winner = max(votes, key=votes.get)
                    pair_scores = [
                        fn(vectors[keys[x]][head], vectors[keys[y]][head])
                        for x, y in ((a, b), (a, c), (b, c))
                    ]
                    if any(s is None or not math.isfinite(s) for s in pair_scores):
                        undefined += 1
                        continue
                    best = max(pair_scores)
                    if name.startswith("topk") and best <= 0:
                        zero_overlap += 1
                        continue
                    if len([v for v in pair_scores if abs(best-v) <= 1e-12]) != 1:
                        metric_ties += 1
                        continue
                    prediction = (c, b, a)[pair_scores.index(best)]
                    pred += 1
                    hit = int(prediction == winner)
                    correct += hit
                    group = ("at_least_70pct" if majority_count /
                             triplets[triple]["total"] >= .7 else "under_70pct")
                    consensus[group][0] += hit
                    consensus[group][1] += 1
                    weighted_votes += votes.get(prediction, 0)
                    eligible_votes += triplets[triple]["total"]
                abstain = undefined + metric_ties + zero_overlap + human_ties
                if pred + abstain != len(selected):
                    raise ValueError("MTT vote accounting is incomplete")
                human_scorable = len(selected) - human_ties
                scores[name] = {
                    "total_unique_unordered_questions": len(selected),
                    "human_tied_majority_questions": human_ties,
                    "human_scorable_questions": human_scorable,
                    "evaluated_questions": pred,
                    "abstained_questions": abstain,
                    "metric_undefined_scores": undefined,
                    "metric_prediction_ties": metric_ties,
                    "metric_zero_overlap": zero_overlap,
                    "prediction_coverage_of_scorable_questions":
                        pred / human_scorable if human_scorable else None,
                    "majority_odd_one_out_accuracy": correct / pred if pred else None,
                    "majority_odd_one_out_correct_count": correct,
                    "majority_accuracy_with_metric_abstentions_as_incorrect":
                        correct / human_scorable if human_scorable else None,
                    "human_vote_weighted_agreement": weighted_votes / eligible_votes
                    if eligible_votes else None,
                    "random_odd_one_out_reference": 1 / 3,
                    "consensus_strata": {
                        key: {"evaluated": n, "correct": hits,
                              "majority_accuracy": hits / n if n else None}
                        for key, (hits, n) in consensus.items()
                    },
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
    p.add_argument("--selection-mode",
                   choices=("smoke", "frozen-development", "all-exploratory"),
                   default="smoke")
    p.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=1)
    p.add_argument("--local-archive-parts", type=Path, nargs=3,
                   help="Three complete and verified official ZIP parts, only runner-private")
    p.add_argument("--seed", type=int, default=20261021)
    args = p.parse_args()
    if args.db.exists() or args.report.exists():
        p.error("Refuse to overwrite old feature sidecar or results")
    for path in (args.comparisons, args.clips, args.tail, args.binary):
        if not path.is_file():
            p.error(f"Missing required input {path}")
    if not args.models_dir.is_dir():
        p.error("Models directory missing")
    if args.selection_mode in ("frozen-development", "all-exploratory"):
        if (digest(args.comparisons) != REGISTERED_MTT_COMPARISONS_SHA256
                or digest(args.clips) != REGISTERED_MTT_CLIPS_SHA256):
            raise ValueError("Frozen artist benchmark source CSV hashes changed")
    triplets, clips = triplets_by_vote(args.comparisons, args.clips)
    if args.selection_mode == "all-exploratory":
        if args.seed != 20261021:
            p.error("Full exploratory cohort must use pinned metadata and seed")
        selected = sorted(triplets)
        if len(selected) != 346 or len({k for group in selected for k in group}) != 1019:
            raise ValueError("Pinned MTT all-triplet/clip cardinality mismatch")
        partition_stats = None
    elif args.selection_mode == "frozen-development":
        if args.development_triplets != 4 or args.seed != 20261021:
            p.error("Frozen-development mode uses the registered 128/256 split and seed")
        selected, partition_stats = frozen_artist_development_selection(triplets, clips)
        if (partition_stats["development_partition_sha256"] !=
                REGISTERED_MTT_DEVELOPMENT_SHA256 or
            partition_stats["holdout_partition_sha256"] !=
                REGISTERED_MTT_HOLDOUT_SHA256):
            raise ValueError("Frozen MTT artist partition changed since preregistration")
    else:
        selected = dev_selection(triplets, clips, args.development_triplets, args.seed)
        partition_stats = None
    members, zipinfo = directory.zip_member_directory(args.tail, args.part_sizes)
    for ident in {c for triple in selected for c in triple}:
        member_lookup(members, clips[ident]["mp3_path"])
    if args.local_archive_parts:
        fetcher = LocalMultipartRanges(args.local_archive_parts, args.part_sizes)
    else:
        fetcher = RangeFetcher(args.part_sizes)
    start = time.monotonic()
    if args.workers > 1:
        keys = sorted({ident for triple in selected for ident in triple})
        def tasks():
            for ident in keys:
                info = member_lookup(members, clips[ident]["mp3_path"])
                yield f"MTT/{ident}.mp3", extract_mp3(info, fetcher)
        diagnostic = analyze_parallel(
            args.binary, args.models_dir, args.db, tasks(),
            {f"MTT/{ident}.mp3" for ident in keys}, args.workers
        )
        diagnostic.update({
            "http_range_requests": fetcher.requests if not args.local_archive_parts else 0,
            "downloaded_audio_zip_bytes": fetcher.total_bytes if not args.local_archive_parts else 0,
            "local_zip_bytes_read": fetcher.total_bytes if args.local_archive_parts else 0,
            "http_request_min_spacing_s": fetcher.min_request_spacing_seconds,
            "http_range_pacing_sleep_seconds":
                round(fetcher.range_pacing_sleep_seconds, 3),
        })
    else:
        diagnostic = run_inference(args.binary, args.models_dir, args.db,
                                   selected, clips, members, fetcher)
        if args.local_archive_parts:
            diagnostic["local_zip_bytes_read"] = fetcher.total_bytes
            diagnostic["downloaded_audio_zip_bytes"] = 0
            diagnostic["http_range_requests"] = 0
    score_begin = time.monotonic()
    results = evaluate(args.db, selected, triplets)
    result = {
        "schema": ("magnatagatune-all-exploratory-v1"
                   if args.selection_mode == "all-exploratory" else
                   "magnatagatune-frozen-artist-development-v1"
                   if partition_stats else "magnatagatune-odd-one-out-development-smoke-v1"),
        "status": ("ALL_346_EXPLORATORY_NO_UNSEEN_MTT_HOLDOUT"
                   if args.selection_mode == "all-exploratory" else
                   "frozen_128_256_artist_development_only_NOT_holdout"
                   if partition_stats else "research_smoke_only_not_a_holdout_or_metric_selection"),
        "source": "https://mirg.city.ac.uk/datasets/magnatagatune/",
        "triplets_scored": len(selected),
        "unique_clip_ids": len({x for triple in selected for x in triple}),
        "seed": args.seed,
        "selection_consensus_minimum": None if partition_stats else 0.7,
        "sampling_policy": (
            "all_346_unique_unordered_triplets_including_former_holdout"
            if args.selection_mode == "all-exploratory" else
            "all_frozen_development_triplets_no_consensus_selection"
            if partition_stats else "high_consensus_disjoint_artist_dev_only"),
        "archive_transfer_policy": ("full_multipart_staged_locally_once"
                                    if args.local_archive_parts else "sparse_http_206_per_clip"),
        "frozen_artist_partition": partition_stats,
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
            "Small same-corpus DEVELOPMENT study or 4-triplet technical smoke; not independent validation.",
            "Frozen development includes all eligible triplets regardless of human vote consensus; smoke selection is high-consensus biased.",
            "In full exploratory mode the original 48 reserved questions ARE analyzed: there is NO independent MTT holdout remaining.",
            "In frozen development mode no artist holdout question is scored.",
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
