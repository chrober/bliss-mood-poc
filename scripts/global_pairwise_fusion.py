#!/usr/bin/env python3
"""Predeclared label-free GLOBAL pairwise cosine fusion candidates.

Experimental: a symmetric song-to-song score with no candidate-set-dependent
ranks, fitted labels, trained individual preferences, or online score scaling.
Scores of different heads may have different empirical distributions even
after affine range mapping. These are ABLATIONS, not calibrated production
similarity probabilities or a universal winner.
"""
from __future__ import annotations

import math

import evaluate_similarity as ev

# Spec fixed before new experimental runs. No searches or fitted weights.
# 87D Genre and 56D Mood use centered cosine; 1280D audio uses cosine.
# All heads are converted from [-1,1] to [0,1] by an AFFINE mapping
# (not empirical CDF, no reference-query-dependent calibration).
# Each included head receives precisely equal fixed weight.
COMPONENTS = {
    "genre_centered": ("genre", ev.centered_cosine),
    "mood_centered": ("moodtheme", ev.centered_cosine),
    "audio": ("embedding", ev.cosine),
}
FUSIONS = {
    "global_genre_mood_equal": ("genre_centered", "mood_centered"),
    "global_genre_audio_equal": ("genre_centered", "audio"),
    "global_mood_audio_equal": ("mood_centered", "audio"),
    "global_genre_mood_audio_equal": ("genre_centered", "mood_centered", "audio"),
}


def pair_score(a: dict, b: dict, method: str) -> float | None:
    """A score depends only on a, b and a frozen method ID, never on other songs.

    Undefined/missing/degenerate/nonfinite inputs result in abstention (None),
    not silently zero-filled/renormalized weights.
    """
    if method not in FUSIONS:
        raise ValueError("Unknown predeclared global fusion")
    similarities = []
    for component in FUSIONS[method]:
        representation, metric = COMPONENTS[component]
        if representation not in a or representation not in b:
            return None
        left, right = a[representation], b[representation]
        if (not isinstance(left, (tuple, list))
                or not isinstance(right, (tuple, list))
                or len(left) != len(right) or len(left) == 0
                or any(not isinstance(x, (int, float)) or isinstance(x, bool)
                       or not math.isfinite(x) for x in (*left, *right))):
            return None
        raw = metric(left, right)
        if raw is None or not math.isfinite(raw) or raw < -1.00000001 or raw > 1.00000001:
            return None
        similarities.append((max(-1.0, min(1.0, raw)) + 1.0) / 2.0)
    if not similarities:
        return None
    return math.fsum(similarities) / len(similarities)


def provenance() -> dict:
    """JSON-safe immutable specification without local music or labels."""
    return {
        "contract": "global_pairwise_equal_weight_affine_cosine_v1",
        "label_fitted_weights": False,
        "preference_training": False,
        "candidate_set_dependent": False,
        "symmetric": True,
        "range": [0.0, 1.0],
        "normalization": "(1 + clipped_cosine) / 2; fixed per pair",
        "weights": "1 / included_head_count",
        "fusions": {name: list(parts) for name, parts in FUSIONS.items()},
        "limitations": (
            "Range mapping does not equalize empirical head distributions. "
            "No claim of calibrated probability or independent metric-selection validation."
        ),
    }
