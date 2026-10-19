#!/usr/bin/env python3
"""Read-only, reproducible comparison of experimental Genre/Mood similarity metrics.

This script deliberately does NOT select a winning metric or calibrate probabilities.
If --labels is omitted, metrics describe their *score distributions*, not quality.
Stdlib only: works with Windows Python without compiling Rust.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import random
import sqlite3
import statistics
import struct
from typing import Callable

MODELS = {"genre": ("genre", 87), "moodtheme": ("mood_theme", 56)}
AGGREGATION = "arithmetic_mean_of_per_patch_sigmoid_scores"
METRICS = ("rms", "cosine", "centered_cosine", "weighted_jaccard", "topk_weighted_jaccard")
MAX_TRACKS = 2000
MAX_RANDOM_PAIRS = 50000
MAX_LABELS = 5000
MIN_ACTIVITY = 0.10


def _finite(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(x) and 0 <= x <= 1 for x in values)


def decode_blob(blob: bytes, dimensions: int) -> tuple[float, ...] | None:
    if not isinstance(blob, bytes) or len(blob) != 4 * dimensions:
        return None
    values = struct.unpack("<" + "f" * dimensions, blob)
    if not _finite(values):
        return None
    mean = sum(values) / len(values)
    if sum((x - mean) ** 2 for x in values) / len(values) <= 1e-10:
        return None
    return values


def rms(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))
    return max(-1.0, min(1.0, 1 - 2 * distance))


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    denom = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / denom if denom > 1e-12 else None


def centered_cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    aa = tuple(x - ma for x in a)
    bb = tuple(x - mb for x in b)
    return cosine(aa, bb)


def weighted_jaccard(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    den = sum(max(x, y) for x, y in zip(a, b))
    return sum(min(x, y) for x, y in zip(a, b)) / den if den > 1e-12 else None


def topk_weighted_jaccard(
    a: tuple[float, ...], b: tuple[float, ...], k: int = 6,
    threshold: float = MIN_ACTIVITY,
) -> float | None:
    if len(a) != len(b) or not a or k < 1:
        return None

    def selected(v: tuple[float, ...]) -> dict[int, float]:
        # Deterministic ordering, even for ties; ignore near-zero activations.
        ranked = sorted(range(len(v)), key=lambda i: (-v[i], i))
        return {i: v[i] for i in ranked[:k] if v[i] >= threshold}

    left, right = selected(a), selected(b)
    keys = left.keys() | right.keys()
    if not keys:
        return None
    den = sum(max(left.get(i, 0.0), right.get(i, 0.0)) for i in keys)
    return sum(min(left.get(i, 0.0), right.get(i, 0.0)) for i in keys) / den if den > 0 else None


METRIC_FUNCS: dict[str, Callable] = {
    "rms": rms,
    "cosine": cosine,
    "centered_cosine": centered_cosine,
    "weighted_jaccard": weighted_jaccard,
    "topk_weighted_jaccard": topk_weighted_jaccard,
}


def describe(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    ordered = sorted(values)

    def percentile(p: float) -> float:
        i = (len(ordered) - 1) * p
        low, high = int(i), min(int(i) + 1, len(ordered) - 1)
        return ordered[low] * (high - i) + ordered[high] * (i - low)

    return {
        "count": len(values), "mean": statistics.fmean(values),
        "p05": percentile(.05), "median": percentile(.5), "p95": percentile(.95),
        "min": ordered[0], "max": ordered[-1],
    }


def auc(positives: list[float], negatives: list[float]) -> float | None:
    """Tie-aware, pairwise ROC-AUC on explicit human-judged labels only."""
    if not positives or not negatives:
        return None
    wins = sum(1 if p > n else .5 if p == n else 0
               for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def _catalog(connection: sqlite3.Connection, model: str, experimental: bool) -> dict:
    capability, dims = MODELS[model]
    rows = connection.execute(
        """SELECT t.model_key, count(*)
           FROM feature_tracks t JOIN feature_models m ON m.model_key = t.model_key
           WHERE t.model_id = ? AND t.capability = ?
           GROUP BY t.model_key ORDER BY count(*) DESC, t.model_key""",
        (model, capability),
    ).fetchall()
    # We must not combine outputs from different classifier fingerprints.
    for key, count in rows:
        meta = connection.execute(
            """SELECT aggregation, classes_json, validated_against_essentia,
                      preprocessing_version
               FROM feature_models WHERE model_key = ?""", (key,),
        ).fetchone()
        if not meta:
            continue
        aggregation, labels_json, validated, preprocessing = meta
        try:
            labels = json.loads(labels_json)
        except (TypeError, ValueError):
            continue
        if (aggregation != AGGREGATION or not preprocessing
            or validated not in (0, 1)
            or not isinstance(labels, list) or len(labels) != dims
            or any(not isinstance(x, str) or not x for x in labels)
            or len(set(labels)) != dims):
            continue
        if not validated and not experimental:
            raise ValueError(
                f"Dominant {model} model cohort is unvalidated; "
                "rerun with --include-experimental for research only."
            )
        return {"model_id": model, "model_key": key, "dimensions": dims,
                "track_count": count, "validated": bool(validated),
                "preprocessing_version": preprocessing}
    raise ValueError(
        f"No eligible {model} cohort (unvalidated model values require "
        "--include-experimental)."
    )


def open_database(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"Feature sidecar does not exist: {path}")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version != 3:
        conn.close()
        raise ValueError(f"Requires feature schema v3, found v{version}")
    return conn


def load_sample(conn: sqlite3.Connection, cohorts: dict, limit: int, seed: int) -> dict:
    # Reservoir sample over all eligible keys: not biased towards earlier artists.
    cur = conn.execute(
        """SELECT g.track_file, g.scores_f32_le, m.scores_f32_le
           FROM feature_tracks g
           JOIN feature_tracks m ON m.track_file = g.track_file AND m.model_id = 'moodtheme'
           WHERE g.model_id = 'genre' AND g.model_key = ?
             AND m.model_key = ?
           ORDER BY g.track_file COLLATE BINARY""",
        (cohorts["genre"]["model_key"], cohorts["moodtheme"]["model_key"]),
    )
    rng = random.Random(seed)
    selected = []
    valid_count = 0
    invalid_count = 0
    for file, genre_blob, mood_blob in cur:
        genre = decode_blob(genre_blob, 87)
        mood = decode_blob(mood_blob, 56)
        if genre is None or mood is None:
            invalid_count += 1
            continue
        valid_count += 1
        item = (file, {"genre": genre, "moodtheme": mood})
        if len(selected) < limit:
            selected.append(item)
        else:
            index = rng.randrange(valid_count)
            if index < limit:
                selected[index] = item
    selected.sort(key=lambda t: t[0])
    return {"tracks": dict(selected), "valid_total": valid_count,
            "invalid": invalid_count, "sample_size": len(selected)}


def evaluate_random(sample: dict, pairs: int, seed: int, examples: int) -> dict:
    tracks = sample["tracks"]
    files = list(tracks)
    if len(files) < 2:
        raise ValueError("Need at least two valid tracks sharing both model cohorts")
    rng = random.Random(seed + 193)
    output = {}
    for head in MODELS:
        scores = {name: [] for name in METRICS}
        for _ in range(pairs):
            a, b = rng.sample(files, 2)
            left, right = tracks[a][head], tracks[b][head]
            for name, function in METRIC_FUNCS.items():
                score = function(left, right)
                if score is not None:
                    scores[name].append(score)
        # Show nearest tracks as *qualitative review prompts*, not labels.
        seed_file = files[0]
        exemplar = []
        for name, function in METRIC_FUNCS.items():
            ranking = []
            for file in files[1:]:
                score = function(tracks[seed_file][head], tracks[file][head])
                if score is not None:
                    ranking.append((score, file))
            ranking.sort(key=lambda row: (-row[0], row[1]))
            exemplar.append({"metric": name, "seed": seed_file,
                             "neighbors": [
                                 {"file": file, "score": score}
                                 for score, file in ranking[:examples]
                             ]})
        output[head] = {"random_pairs": {name: describe(v) for name, v in scores.items()},
                        "nearest_neighbor_examples": exemplar}
    return output


def load_labels(path: Path) -> list[tuple[str, str, int]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"left", "right", "label"} <= set(reader.fieldnames):
            raise ValueError("Label CSV requires left,right,label columns")
        labels = []
        seen = set()
        for row in reader:
            a, b = row["left"], row["right"]
            label = row["label"].strip()
            if not a or not b or a == b or label not in ("0", "1"):
                raise ValueError("Judged pairs must contain distinct exact file keys and label 0/1")
            pair = tuple(sorted((a, b)))
            if pair in seen:
                raise ValueError("Duplicate judged pair; do not give it extra weight")
            seen.add(pair)
            labels.append((a, b, int(label)))
            if len(labels) > MAX_LABELS:
                raise ValueError(f"At most {MAX_LABELS} judged pairs")
    return labels


def fetch_keys(conn: sqlite3.Connection, keys: set[str], cohorts: dict) -> dict:
    found: dict[str, dict] = {}
    for key in sorted(keys):
        heads = {}
        for model, meta in cohorts.items():
            row = conn.execute(
                """SELECT scores_f32_le FROM feature_tracks
                   WHERE track_file = ? COLLATE BINARY AND model_id = ?
                     AND model_key = ?""",
                (key, model, meta["model_key"]),
            ).fetchone()
            if row:
                decoded = decode_blob(row[0], meta["dimensions"])
                if decoded is not None:
                    heads[model] = decoded
        found[key] = heads
    return found


def evaluate_labels(conn: sqlite3.Connection, cohorts: dict, labels: list) -> dict:
    found = fetch_keys(conn, {name for a, b, _ in labels for name in (a, b)}, cohorts)
    result = {"judged_pairs": len(labels), "method": "manual_positive_negative_labels"}
    for head in MODELS:
        by_method = {name: {0: [], 1: []} for name in METRICS}
        unmatched = 0
        for a, b, label in labels:
            if head not in found[a] or head not in found[b]:
                unmatched += 1
                continue
            for metric, function in METRIC_FUNCS.items():
                value = function(found[a][head], found[b][head])
                if value is not None:
                    by_method[metric][label].append(value)
        result[head] = {
            "pairs_missing_compatible_vectors": unmatched,
            "metrics": {
                name: {
                    "positives": describe(sets[1]),
                    "negatives": describe(sets[0]),
                    "roc_auc": auc(sets[1], sets[0]),
                    "status": "judged" if sets[1] and sets[0]
                              else "insufficient_both_classes",
                } for name, sets in by_method.items()
            },
        }
    return result


def report(database: Path, limit: int, pairs: int, seed: int, examples: int,
           experimental: bool, label_path: Path | None) -> dict:
    with closing(open_database(database)) as conn:
        cohorts = {model: _catalog(conn, model, experimental) for model in MODELS}
        sample = load_sample(conn, cohorts, limit, seed)
        if sample["sample_size"] < 2:
            raise ValueError("Insufficient matching valid Genre/Mood vectors")
        out = {
            "schema": "similarity-metric-evaluation-v1",
            "mode": "experimental" if not all(x["validated"] for x in cohorts.values())
                        else "validated-heads",
            "warning": "Unlabeled rankings are NOT evidence of musical similarity quality. "
                       "ROC-AUC uses only user-supplied labels. Scores are not calibrated probabilities.",
            "source": {"feature_schema": 3, "read_only": True,
                       "audio_or_onnx_access": False},
            "models": cohorts,
            "sampling": {"seed": seed, "limit": limit, "pairs_requested": pairs,
                         "paired_valid_total": sample["valid_total"],
                         "paired_invalid": sample["invalid"],
                         "sample_size": sample["sample_size"]},
            "unlabeled": evaluate_random(sample, pairs, seed, examples),
        }
        if label_path:
            out["labeled"] = evaluate_labels(conn, cohorts, load_labels(label_path))
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True,
                        help="Existing schema-v3 feature sidecar; opened read-only")
    parser.add_argument("--include-experimental", action="store_true",
                        help="Explicitly permit not-yet-validated model vectors")
    parser.add_argument("--limit", type=int, default=300,
                        help="Reservoir sample size (2..2000; default 300)")
    parser.add_argument("--pairs", type=int, default=3000,
                        help="Random pair comparisons per head (1..50000; default 3000)")
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--examples", type=int, default=5,
                        help="Nearest tracks per metric for manual listening (0..20)")
    parser.add_argument("--labels", type=Path,
                        help="Optional user-judged CSV with exact left,right,label(0/1)")
    args = parser.parse_args()
    if not 2 <= args.limit <= MAX_TRACKS or not 1 <= args.pairs <= MAX_RANDOM_PAIRS:
        parser.error("Limit or pairs outside permitted range")
    if not 0 <= args.examples <= 20:
        parser.error("Examples outside 0..20")
    try:
        out = report(args.db, args.limit, args.pairs, args.seed, args.examples,
                     args.include_experimental, args.labels)
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        parser.exit(2, f"Similarity evaluation failed: {exc}\n")
    print(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
