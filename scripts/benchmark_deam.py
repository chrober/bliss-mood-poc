#!/usr/bin/env python3
"""Reproducible DEAM valence/arousal retrieval benchmark (Python stdlib only).

Research only. No listener ratings are inferred from filenames or model scores.
The DEAM noncommercial audio, annotations, and per-song features stay in an
ignored local working directory; reports contain aggregates, not music data.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import zipfile

import evaluate_similarity as ev

DEAM_SOURCE = "https://cvml.unige.ch/databases/DEAM/"
AUDIO_NAME = re.compile(r"^([0-9]+)\.mp3$", re.IGNORECASE)
ANNOTATION_NAME = re.compile(
    r"^static_annotations_averaged_songs_[0-9_]+\.csv$", re.IGNORECASE
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_annotations(path: Path) -> dict[str, tuple[float, float]]:
    """Read DEAM song-level human label means, scale 1..9, keyed by numeric id."""
    result: dict[str, tuple[float, float]] = {}
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist()
                 if ANNOTATION_NAME.fullmatch(Path(n).name)]
        if not names:
            raise ValueError("No DEAM song-level static averaged annotation CSV found")
        for name in sorted(names):
            with archive.open(name) as handle:
                reader = csv.DictReader(io.TextIOWrapper(
                    handle, encoding="utf-8-sig", newline=""
                ))
                if reader.fieldnames is None:
                    raise ValueError(f"Empty annotation file: {name}")
                if not {"song_id", "valence_mean", "arousal_mean"} <= {
                    col.strip() for col in reader.fieldnames
                }:
                    raise ValueError(f"Wrong annotation columns in {name}")
                for original in reader:
                    row = {key.strip(): value for key, value in original.items()}
                    identifier = row["song_id"].strip()
                    try:
                        number = int(identifier)
                        valence = float(row["valence_mean"])
                        arousal = float(row["arousal_mean"])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Invalid DEAM annotation in {name}") from exc
                    if number < 1 or not all(
                        math.isfinite(v) and 1 <= v <= 9
                        for v in (valence, arousal)
                    ):
                        raise ValueError(f"Out of range annotation in {name}")
                    key = str(number)
                    values = (valence, arousal)
                    if key in result and result[key] != values:
                        raise ValueError(f"Conflicting annotation for DEAM ID {key}")
                    result[key] = values
    if not result:
        raise ValueError("No valid DEAM song-level annotations")
    return result


def match_audio(path: Path, annotated: dict) -> dict[str, str]:
    """Index audio by numeric basename; reject ambiguous IDs, never extract all."""
    matches: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            match = AUDIO_NAME.fullmatch(Path(item.filename).name)
            if not match or int(match.group(1)) < 1:
                continue
            key = str(int(match.group(1)))
            if key not in annotated:
                continue
            if key in matches:
                raise ValueError(f"Ambiguous MP3s for DEAM ID {key}")
            if item.file_size < 1024 or item.file_size > 80 * 1024 * 1024:
                raise ValueError(f"Unreasonable MP3 size for DEAM ID {key}")
            matches[key] = item.filename
    if len(matches) < 6:
        raise ValueError(
            f"Only {len(matches)} DEAM audio tracks match numeric annotations"
        )
    return matches


def select_ids(annotations: dict, available: dict, limit: int, seed: int) -> list[str]:
    """Seeded, fixed subset with reproducible behavior for subsequent reruns."""
    common = sorted(set(annotations) & set(available), key=int)
    if limit < 6 or limit > len(common):
        raise ValueError(f"Requested {limit} DEAM songs, available {len(common)}")
    random.Random(seed).shuffle(common)
    return common[:limit]


def run_inference(binary: Path, models_dir: Path, audio_zip: Path, ids: list[str],
                  members: dict[str, str], database: Path) -> None:
    if database.exists():
        raise FileExistsError(f"Refuse to overwrite existing benchmark DB: {database}")
    database.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(audio_zip) as archive:
        for index, identifier in enumerate(ids, 1):
            # Extract exactly one file at a time to limit scratch-disk usage.
            with tempfile.TemporaryDirectory(prefix="deam-track-") as tmp:
                source = Path(tmp) / (identifier + ".mp3")
                with archive.open(members[identifier]) as src, source.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
                command = [
                    str(binary.resolve()), "analyze-features", str(source),
                    "--models-dir", str(models_dir.resolve()),
                    "--models", "genre,moodtheme",
                    "--threads", "1", "--db", str(database.resolve()),
                    "--track-key", f"DEAM/{identifier}.mp3",
                ]
                completed = subprocess.run(
                    command, capture_output=True, text=True, timeout=900,
                    check=False,
                )
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"DEAM feature extraction failed for item {index}/{len(ids)}: "
                        f"{completed.stderr[-2500:]}"
                    )
            print(f"Analyzed DEAM item {index}/{len(ids)}", flush=True)


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.] * len(values)
    position = 0
    while position < len(order):
        end = position + 1
        while end < len(order) and values[order[end]] == values[order[position]]:
            end += 1
        rank = (position + 1 + end) / 2
        for index in order[position:end]:
            ranks[index] = rank
        position = end
    return ranks


def pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(a) != len(b):
        return None
    mean_a = statistics.fmean(a)
    mean_b = statistics.fmean(b)
    da = [v - mean_a for v in a]
    db = [v - mean_b for v in b]
    denom = math.sqrt(sum(v*v for v in da) * sum(v*v for v in db))
    return sum(x*y for x, y in zip(da, db)) / denom if denom > 1e-12 else None


def spearman(a: list[float], b: list[float]) -> float | None:
    return pearson(average_ranks(a), average_ranks(b))


def bootstrap_ci(values: list[float], seed: int, rounds: int = 400) -> list[float]:
    """Exploratory resampling of query-level scores (queries also share tracks)."""
    rng = random.Random(seed)
    n = len(values)
    simulated = sorted(
        statistics.fmean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(rounds)
    )
    return [simulated[int(rounds * .025)], simulated[int(rounds * .975)]]


def evaluate(database: Path, identifiers: list[str], annotations: dict, seed: int) -> dict:
    keys = {key: f"DEAM/{key}.mp3" for key in identifiers}
    with closing(ev.open_database(database)) as connection:
        cohorts = {head: ev._catalog(connection, head, experimental=True)
                   for head in ev.MODELS}
        if any("essentia-audio-v5" not in info["preprocessing_version"]
               for info in cohorts.values()):
            raise ValueError("DEAM benchmark requires corrected Rust-v5 feature cohorts")
        vectors = ev.fetch_keys(connection, set(keys.values()), cohorts)
        for song_id, track_key in keys.items():
            if set(vectors[track_key]) != set(ev.MODELS):
                raise ValueError(f"Missing compatible DEAM feature vectors: {song_id}")
        output = {}
        for head in ev.MODELS:
            results = {}
            for metric, metric_fn in ev.METRIC_FUNCS.items():
                query_scores = {"valence": [], "arousal": [], "valence_arousal": []}
                skipped = 0
                for anchor in identifiers:
                    a = vectors[keys[anchor]][head]
                    similarities = []
                    target = {"valence": [], "arousal": [], "valence_arousal": []}
                    for other in identifiers:
                        if other == anchor:
                            continue
                        score = metric_fn(a, vectors[keys[other]][head])
                        if score is None or not math.isfinite(score):
                            continue
                        va = annotations[anchor]
                        vb = annotations[other]
                        vdist = abs(va[0] - vb[0])
                        adist = abs(va[1] - vb[1])
                        similarities.append(score)
                        target["valence"].append(-vdist)
                        target["arousal"].append(-adist)
                        target["valence_arousal"].append(-math.hypot(vdist, adist))
                    if len(similarities) < 5:
                        skipped += 1
                        continue
                    for axis in query_scores:
                        rho = spearman(similarities, target[axis])
                        if rho is not None:
                            query_scores[axis].append(rho)
                metrics = {}
                for axis, values in query_scores.items():
                    metrics[axis] = {
                        "query_count": len(values),
                        "mean_query_spearman": statistics.fmean(values) if values else None,
                        "query_bootstrap_95pct": bootstrap_ci(values, seed) if len(values) >= 6 else None,
                    }
                results[metric] = {
                    "axes": metrics,
                    "queries_insufficient_defined_scores": skipped,
                }
            output[head] = results
        return {
            "schema": "deam-similarity-benchmark-v1",
            "dataset": {"name": "DEAM", "source": DEAM_SOURCE,
                        "license": "CC BY-NC (dataset manual)",
                        "label_type": "human song-level valence/arousal averages",
                        "label_range": [1, 9], "songs_evaluated": len(identifiers),
                        "sampling_seed": seed},
            "caveats": [
                "Valence/arousal proximity is a proxy, not direct human pairwise similarity.",
                "Metrics and model heads are exploratory; no winner is selected.",
                "Bootstrap re-samples queries that share underlying tracks; intervals are descriptive.",
                "This benchmark has no audio, names, label rows, or per-track scores in the report.",
            ],
            "models": {h: {"model_key": m["model_key"],
                           "preprocessing_version": m["preprocessing_version"]}
                       for h, m in cohorts.items()},
            "per_head": output,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations-zip", type=Path, required=True)
    parser.add_argument("--audio-zip", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()
    if not 6 <= args.limit <= 1802:
        parser.error("--limit must be between 6 and 1802")
    if args.report.exists() or args.db.exists():
        parser.error("Output report or feature database already exists; no overwrites")
    for path in (args.audio_zip, args.annotations_zip, args.binary):
        if not path.is_file():
            parser.error(f"Missing input: {path}")
    if not args.models_dir.is_dir():
        parser.error("Missing models directory")
    annotations = load_annotations(args.annotations_zip)
    members = match_audio(args.audio_zip, annotations)
    ids = select_ids(annotations, members, args.limit, args.seed)
    print(f"Matched {len(members)} annotated MP3s; using {len(ids)} (seed={args.seed}).")
    run_inference(args.binary, args.models_dir, args.audio_zip, ids, members, args.db)
    result = evaluate(args.db, ids, annotations, args.seed)
    result["dataset"]["annotation_archive_sha256"] = sha256_file(args.annotations_zip)
    result["dataset"]["audio_archive_sha256"] = sha256_file(args.audio_zip)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "songs_evaluated": result["dataset"]["songs_evaluated"],
        "report": str(args.report),
        "mood_cosine_va": result["per_head"]["moodtheme"]["cosine"]["axes"]["valence_arousal"],
    }, indent=2))


if __name__ == "__main__":
    main()
