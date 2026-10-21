#!/usr/bin/env python3
"""Paired, in-memory MagnaTagATune sensitivity analysis (no per-track export).

Outcomes are aligned per unique *unordered* human triplet, with metric
abstentions scored as zero on a common denominator (excludes human ties).
Two sensitivity intervals are displayed: naive paired triplet resampling,
and artist-weight perturbations. Neither is a confidence interval for
independent out-of-corpus generalization: all 214 artists are joined in
a single co-occurrence component. No metric choice or p-value.
"""
from __future__ import annotations

import math
import random

DEFAULT_REPLICATES = 600
DEFAULT_SEED = 20261021


def quantile(values: list[float], fraction: float) -> float:
    if not values or not 0 <= fraction <= 1:
        raise ValueError("Invalid quantile sample/fraction")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def paired_sensitivity(rows: list[dict], methods: list[str],
                       seed: int = DEFAULT_SEED,
                       replicates: int = DEFAULT_REPLICATES) -> dict:
    """Rows contain booleans (abstentions as 0), plus private artist labels.

    Privacy: returns only aggregate method-pair differences and summary
    metadata. No identifiers, song vectors, votes, or per-question
    outcomes leave memory.
    """
    if not rows or not 2 <= len(methods) <= 20 or len(set(methods)) != len(methods):
        raise ValueError("Invalid paired benchmark cohort/metrics")
    if not 100 <= replicates <= 5000:
        raise ValueError("Sensitivity replicates must be 100..5000")
    n = len(rows)
    for row in rows:
        if set(row["outcomes"]) != set(methods):
            raise ValueError("Missing paired method on a common reference question")
        if not row["artists"] or any(not x for x in row["artists"]):
            raise ValueError("Artist metadata incomplete: cluster sensitivity invalid")
        if any(v not in (0, 1) for v in row["outcomes"].values()):
            raise ValueError("Only paired 0/1/abstention-as-zero outcomes allowed")
    artists = sorted(set(a for row in rows for a in row["artists"]))
    vectors = [[row["outcomes"][m] for row in rows] for m in methods]
    means = [sum(x)/n for x in vectors]

    # Shared bootstrap resamples across ALL seven methods preserve
    # within-question pairing; they do not account for song dependence.
    naive_rng = random.Random(seed)
    iid = [[] for _ in methods]
    for _ in range(replicates):
        indices = [naive_rng.randrange(n) for _ in range(n)]
        for ix, scores in enumerate(vectors):
            iid[ix].append(sum(scores[i] for i in indices) / n)

    # Stress test: draw shared positive random weights per artist,
    # weight each question by the mean weight of its artists.
    # This is a dependency sensitivity perturbation, NOT a valid
    # graph-cluster bootstrap or population CI. A single connected
    # artist component prevents clean group resampling.
    rng = random.Random(seed + 17)
    deps = [[artists.index(a) for a in sorted(set(row["artists"]))]
            for row in rows]
    artist_weighted = [[] for _ in methods]
    for _ in range(replicates):
        w = [rng.expovariate(1.0) for _ in artists]
        question_w = [sum(w[a] for a in group) / len(group) for group in deps]
        denom = sum(question_w)
        for ix, scores in enumerate(vectors):
            artist_weighted[ix].append(
                sum(v * ww for v, ww in zip(scores, question_w)) / denom
            )

    comparisons = []
    for i, left in enumerate(methods):
        for j in range(i + 1, len(methods)):
            right = methods[j]
            diff = means[i] - means[j]
            only_left = sum(a == 1 and b == 0 for a, b
                            in zip(vectors[i], vectors[j]))
            only_right = sum(a == 0 and b == 1 for a, b
                             in zip(vectors[i], vectors[j]))
            iid_differences = [a-b for a,b in zip(iid[i],iid[j])]
            artist_differences = [a-b for a,b in zip(artist_weighted[i],
                                                     artist_weighted[j])]
            comparisons.append({
                "metric_a": left,
                "metric_b": right,
                "common_human_scorable_questions": n,
                "a_only_correct": only_left,
                "b_only_correct": only_right,
                "paired_accuracy_delta_pp": round(100 * diff, 3),
                "iid_question_bootstrap_95pct_delta_pp": [
                    round(100 * quantile(iid_differences, .025), 3),
                    round(100 * quantile(iid_differences, .975), 3)
                ],
                "artist_weight_sensitivity_95pct_delta_pp": [
                    round(100 * quantile(artist_differences, .025), 3),
                    round(100 * quantile(artist_differences, .975), 3)
                ],
            })
    return {
        "schema": "mtt-paired-seven-method-artist-sensitivity-v1",
        "selection_status": "exploratory_same_corpus_NO_holdout",
        "method_count": len(methods),
        "comparison_count": len(comparisons),
        "common_human_scorable_questions": n,
        "different_artists_referenced": len(artists),
        "resampling_replicates": replicates,
        "seed": seed,
        "methods": {
            method: {"correct_including_metric_abstentions_as_zero":
                     sum(vectors[i]),
                     "accuracy_including_metric_abstentions_as_zero": means[i]}
            for i, method in enumerate(methods)
        },
        "paired_comparisons": comparisons,
        "limits": [
            "Differences are on the exact same human-majority-scorable triplets; metric abstentions count as incorrect.",
            "IID triplet intervals assume independent questions, which is false for shared songs/artists.",
            "Artist-weight intervals are exploratory dependency sensitivity, NOT valid population confidence intervals.",
            "All artist co-occurrences form one graph component: a valid artist-component bootstrap is impossible.",
            "Twenty-one post-hoc method comparisons per head are exploratory and not multiplicity-adjusted.",
            "No preserved independent MTT test set remains and encoder training leakage was not ruled out.",
            "No per-track human votes, clip IDs, features, raw predictions or artist names are exported.",
        ],
    }
