#!/usr/bin/env python3
"""Predeclared equal-weight rank fusion of already-computed song representations.

This is a *triplet-local experimental ablation*, not a globally comparable
Lyrion similarity score or a learned calibration. No weights are optimized.
"""
from __future__ import annotations

import math

import evaluate_similarity as ev

# Deliberately frozen PRIOR to inspecting fusion outputs.
FIXED_FUSIONS: dict[str, tuple[str, ...]] = {
    "rank_audio_genre_equal": ("embedding", "genre"),
    "rank_audio_mood_equal": ("embedding", "moodtheme"),
    "rank_genre_mood_equal": ("genre", "moodtheme"),
    "rank_audio_genre_mood_equal": ("embedding", "genre", "moodtheme"),
}


def scores_to_local_ranks(pair_scores: list[float]) -> tuple[float, float, float]:
    """Three-pair midranks normalized to [0,1] (low=0, high=1).

    Ties within an explicit 1e-12 tolerance share the mean rank, without
    relying on pair order for tie breaking. No training/calibration inputs.
    """
    if len(pair_scores) != 3 or any(not math.isfinite(s) for s in pair_scores):
        raise ValueError("Expected three finite pair similarities")
    order = sorted(range(3), key=lambda i: (pair_scores[i], i))
    rank = [0.0] * 3
    i = 0
    while i < 3:
        j = i + 1
        while j < 3 and abs(pair_scores[order[j]] - pair_scores[order[i]]) <= 1e-12:
            j += 1
        midrank = ((i + j - 1) / 2.0) / 2.0
        for position in order[i:j]:
            rank[position] = midrank
        i = j
    return tuple(rank)


def predict(triple: tuple[str, str, str], vector_by_id: dict,
            representations: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Choose odd-one-out by the equally averaged *within-triplet pair rank*."""
    if len(triple) != 3 or len(set(triple)) != 3:
        raise ValueError("Expected three distinct song identities")
    if not 2 <= len(representations) <= 3 or len(set(representations)) != len(representations):
        raise ValueError("Equal-weight rank fusion requires two or three distinct representations")
    if any(name not in {"embedding", "genre", "moodtheme"} for name in representations):
        raise ValueError("Unsupported representation in frozen rank fusion")
    a, b, c = triple
    pairs = ((a, b), (a, c), (b, c))
    pooled = [0.0] * 3
    for head in representations:
        pair_scores = []
        for x, y in pairs:
            if x not in vector_by_id or y not in vector_by_id:
                raise ValueError("Missing song from common A/B/C cohort")
            score = ev.cosine(vector_by_id[x][head], vector_by_id[y][head])
            if score is None or not math.isfinite(score):
                return None, "undefined"
            pair_scores.append(score)
        ranks = scores_to_local_ranks(pair_scores)
        for j in range(3):
            pooled[j] += ranks[j] / len(representations)
    best = max(pooled)
    if sum(abs(s - best) <= 1e-12 for s in pooled) != 1:
        return None, "tie"
    return (c, b, a)[pooled.index(best)], None
