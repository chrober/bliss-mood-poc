#!/usr/bin/env python3
"""Prepare a metric-blind, deterministic listening-pair CSV from schema-v3 features.

This is sampling for HUMAN listening review, not a metric winner selector.
The feature model's scores are NEVER treated as human genre/mood labels.
An independent hidden audit records why the pairs were proposed; do not
look at the audit until after completing the listening judgments.
Only existing SQLite schema-v3 sidecars are read (read-only; no ONNX/audio).
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from contextlib import closing
import csv
import itertools
import json
import math
from pathlib import Path
import random

import evaluate_similarity as ev

MAX_TRACKS = 300
MAX_POOL_PAIRS = 20000
V5_PREPROCESSING = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"

# These are sampling strata, NOT musical labels or claims of accuracy.
STRATA = (
    "high_both", "genre_high_mood_low", "mood_high_genre_low",
    "low_both", "genre_metric_disagreement", "mood_metric_disagreement",
    "low_mood_activation", "random_control",
)


def percentile(values: list[float], current: float) -> float:
    """Relative within-candidate-pool position (NOT probability of similarity)."""
    if not values:
        raise ValueError("No defined candidates")
    return bisect_right(values, current) / len(values)


def select_review_pairs(sample: dict, count: int, seed: int,
                        pool_pairs: int = MAX_POOL_PAIRS) -> tuple[list[dict], dict]:
    """Distinct reviewer prompts plus a *separate, private* selection audit.

    Repeated seed songs are capped where feasible. All pairwise score
    computations are bounded and the algorithm never infers labels from names.
    """
    tracks = sample["tracks"]
    files = sorted(tracks)
    n = len(files)
    if not 6 <= n <= MAX_TRACKS:
        raise ValueError(f"Require 6..{MAX_TRACKS} valid independent tracks")
    combinations = n * (n - 1) // 2
    if not 6 <= count <= min(100, combinations):
        raise ValueError("Require 6..100 distinct review pairs, within available tracks")
    if not count <= pool_pairs <= MAX_POOL_PAIRS:
        raise ValueError("pool-pairs must be >= count and <= 20000")
    rng = random.Random(seed + 101)
    # 300 tracks = 44,850 index pairs, bounded even before score sampling.
    all_indices = itertools.combinations(range(n), 2)
    if combinations <= pool_pairs:
        pool = list(all_indices)
    else:
        # Uniform reservoir sample: never build a full large pair matrix.
        pool = []
        for seen, indices in enumerate(all_indices):
            if seen < pool_pairs:
                pool.append(indices)
            else:
                replacement = rng.randrange(seen + 1)
                if replacement < pool_pairs:
                    pool[replacement] = indices
    pool.sort()

    # Record only finite metrics; undefined Top-K scores are not high-ranked.
    # Both heads are represented on their own within-cohort distributions.
    raw = []
    for a, b in pool:
        left, right = tracks[files[a]], tracks[files[b]]
        metrics = {}
        for head in ev.MODELS:
            c = ev.cosine(left[head], right[head])
            top = ev.METRIC_FUNCS["topk6_ranked_jaccard"](left[head], right[head])
            metrics[head] = {"cosine": c, "ranked_top6": top}
        if any(value is None or not math.isfinite(value)
               for head in ev.MODELS for value in metrics[head].values()):
            continue
        raw.append({"key": (files[a], files[b]), "scores": metrics,
                    "low_mood": max(left["moodtheme"]) < .10
                                or max(right["moodtheme"]) < .10})
    if len(raw) < count:
        raise ValueError("Insufficient pairs with both independently defined heads")

    ordered = {
        (head, metric): sorted(row["scores"][head][metric] for row in raw)
        for head in ev.MODELS for metric in ("cosine", "ranked_top6")
    }
    for row in raw:
        row["percentiles"] = {
            head: {
                metric: percentile(ordered[(head, metric)], row["scores"][head][metric])
                for metric in ("cosine", "ranked_top6")
            } for head in ev.MODELS
        }

    categories: dict[str, list[tuple[float, dict]]] = {key: [] for key in STRATA}
    for row in raw:
        g = row["percentiles"]["genre"]["cosine"]
        m = row["percentiles"]["moodtheme"]["cosine"]
        gt = row["percentiles"]["genre"]["ranked_top6"]
        mt = row["percentiles"]["moodtheme"]["ranked_top6"]
        if g >= .8 and m >= .8:
            categories["high_both"].append((min(g, m), row))
        if g >= .8 and m <= .25:
            categories["genre_high_mood_low"].append((g - m, row))
        if m >= .8 and g <= .25:
            categories["mood_high_genre_low"].append((m - g, row))
        if g <= .25 and m <= .25:
            categories["low_both"].append((2 - g - m, row))
        if abs(g - gt) >= .40:
            categories["genre_metric_disagreement"].append((abs(g - gt), row))
        if abs(m - mt) >= .40:
            categories["mood_metric_disagreement"].append((abs(m - mt), row))
        if row["low_mood"]:
            categories["low_mood_activation"].append((1 - m, row))
        categories["random_control"].append((rng.random(), row))

    for category, rows in categories.items():
        rows.sort(key=lambda item: (-item[0], item[1]["key"]))

    selected, used, appearances = [], set(), Counter()
    # Round-robin quotas, followed by a deterministic fallback if a
    # particular cohort lacks cross-head-discordant/low-activity examples.
    positions = {category: 0 for category in STRATA}
    for cap in (2, 3, 5, count):
        while len(selected) < count:
            changed = False
            for category in STRATA:
                candidates = categories[category]
                while positions[category] < len(candidates):
                    row = candidates[positions[category]][1]
                    positions[category] += 1
                    a, b = row["key"]
                    if row["key"] in used or appearances[a] >= cap or appearances[b] >= cap:
                        continue
                    used.add(row["key"])
                    appearances[a] += 1
                    appearances[b] += 1
                    selected.append({"key": row["key"], "stratum": category,
                                     "scores": row["scores"],
                                     "percentiles": row["percentiles"]})
                    changed = True
                    break
                if len(selected) == count:
                    break
            if not changed:
                break
        if len(selected) == count:
            break
        # Retry previously rejected pairs at the relaxed appearance bound.
        positions = {category: 0 for category in STRATA}
    if len(selected) != count:
        raise AssertionError("Could not fill bounded listening sample")

    # Shuffle order and left/right presentation so the CSV does not encode
    # the sampling stratum or which of the two items was treated as seed.
    rng.shuffle(selected)
    public = []
    private = []
    for i, row in enumerate(selected, 1):
        a, b = row["key"]
        if rng.getrandbits(1):
            a, b = b, a
        public.append({"left": a, "right": b, "genre_label": "", "mood_label": ""})
        private.append({"pair_number": i, "left": a, "right": b,
                        "sampling_stratum_not_a_label": row["stratum"],
                        "raw_scores_not_probabilities": row["scores"],
                        "within_pool_percentiles_not_probabilities": row["percentiles"]})
    return public, {
        "requested_pairs": count, "selected_pairs": len(public),
        "sampled_tracks": n, "candidate_pairs_considered": len(raw),
        "stratum_counts": dict(Counter(x["sampling_stratum_not_a_label"] for x in private)),
        "pair_selection_audit": private,
        "warning": "All genre_label/mood_label cells intentionally blank. "
                   "Never derive listening truth from model metrics or filenames. "
                   "Keep this audit sealed until after independent listening.",
    }


def create_review_files(db: Path, out_dir: Path, limit: int, count: int,
                        seed: int, pool_pairs: int, require_v5: bool) -> dict:
    if out_dir.exists():
        raise FileExistsError("Use a NEW output directory; do not overwrite listening judgments")
    if not 6 <= limit <= MAX_TRACKS:
        raise ValueError("Sample limit must be 6..300")
    with closing(ev.open_database(db)) as conn:
        cohorts = {model: ev._catalog(conn, model, experimental=True)
                   for model in ev.MODELS}
        if require_v5:
            for head, meta in cohorts.items():
                if meta["preprocessing_version"] != V5_PREPROCESSING:
                    raise ValueError(
                        f"{head}: expected actual corrected Rust v5 preprocessing "
                        f"fingerprint, found {meta['preprocessing_version']!r}"
                    )
        sample = ev.load_sample(conn, cohorts, limit, seed)
        selected, audit = select_review_pairs(sample, count, seed, pool_pairs)
    # Only create files after preflight, and never expose the audit in the
    # blinded CSV or stdout. Old SQLite features remain untouched.
    audit["mode"] = "experimental_model_vectors_do_not_imply_musical_quality"
    audit["source"] = {
        "input_read_only": True, "audio_or_onnx_access": False,
        "schema": 3, "models": {
            head: {k: meta[k] for k in ("model_key", "preprocessing_version",
                                       "validated", "track_count")}
            for head, meta in cohorts.items()
        },
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        with (out_dir / "listening-pairs.csv").open(
            "x", newline="", encoding="utf-8-sig"
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["left", "right", "genre_label", "mood_label"]
            )
            writer.writeheader()
            writer.writerows(selected)
        (out_dir / "selection-audit-private.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        # Preserve partial contents for diagnosis, never overwrite on rerun.
        raise
    return {
        "status": "READY_FOR_HUMAN_LISTENING",
        "pairs": len(selected),
        "genre_labels_filled": 0, "mood_labels_filled": 0,
        "sampled_tracks": audit["sampled_tracks"],
        "candidate_pairs_considered": audit["candidate_pairs_considered"],
        "stratum_counts": audit["stratum_counts"],
        "model_validation_status": {
            head: ("validated" if meta["validated"] else "experimental")
            for head, meta in cohorts.items()
        },
        "review_csv": str(out_dir / "listening-pairs.csv"),
        "sealed_private_selection_audit": str(out_dir / "selection-audit-private.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--pool-pairs", type=int, default=MAX_POOL_PAIRS)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--require-v5", action="store_true",
                        help="Reject any model cohort not using verified Rust-v5 preprocessing identity")
    args = parser.parse_args()
    print(json.dumps(create_review_files(
        args.db, args.out_dir, args.limit, args.count,
        args.seed, args.pool_pairs, args.require_v5
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
