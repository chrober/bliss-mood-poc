#!/usr/bin/env python3
"""WP3-R1 descriptive Bliss 23D / Essentia head relationships, NO fitted model.

Synthetic/in-memory experiment. Select strongest relationships by train-only
Spearman; report their holdout correlation on disjoint recording/artist/album
groups. Essentia teacher scores are not independent musical ground truth.
No library scan, raw data output, or personal preference training.
"""
from __future__ import annotations

from collections import Counter
import math
from statistics import median
from typing import Mapping, Sequence

from research_grouped_split import grouped_partition, Partition

BLISS_COLUMNS = (
    "Tempo", "Zcr", "MeanSpectralCentroid", "StdDevSpectralCentroid",
    "MeanSpectralRolloff", "StdDevSpectralRolloff",
    "MeanSpectralFlatness", "StdDevSpectralFlatness",
    "MeanLoudness", "StdDevLoudness",
    "Chroma1", "Chroma2", "Chroma3", "Chroma4", "Chroma5", "Chroma6",
    "Chroma7", "Chroma8", "Chroma9", "Chroma10", "Chroma11",
    "Chroma12", "Chroma13",
)
HEAD_DIMS = {"genre": 87, "moodtheme": 56}
MAX_RECORDINGS = 4000
MIN_PARTITION = 4


def _average_ranks(values: Sequence[float]) -> list[float]:
    sorted_idx = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for i in range(len(values)):
        if ranks[sorted_idx[i]]:
            continue
        j = i+1
        while j < len(values) and values[sorted_idx[j]] == values[sorted_idx[i]]:
            j += 1
        rank = (i + j - 1) / 2 + 1
        for k in range(i, j):
            ranks[sorted_idx[k]] = rank
    return ranks


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < MIN_PARTITION:
        return None
    mx, my = math.fsum(x)/len(x), math.fsum(y)/len(y)
    dx, dy = [a-mx for a in x], [b-my for b in y]
    a, b = math.fsum(v*v for v in dx), math.fsum(v*v for v in dy)
    if a <= 1e-24 or b <= 1e-24:
        return None
    rho = math.fsum(v*w for v, w in zip(dx, dy)) / math.sqrt(a*b)
    return max(-1.0, min(1.0, rho))


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < MIN_PARTITION:
        return None
    return pearson(_average_ranks(x), _average_ranks(y))


def _vector(row: Mapping, key: str, dims: int) -> tuple[float, ...]:
    values = row.get(key)
    if (not isinstance(values, (tuple, list)) or len(values) != dims
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise ValueError("Missing, malformed or nonfinite paired feature vectors")
    if key != "bliss" and any(not 0.0 <= v <= 1.0 for v in values):
        raise ValueError("Classifier scores outside expected experimental range")
    return tuple(float(v) for v in values)


def _summary(
    rows: Sequence[Mapping], train: Sequence[int], test: Sequence[int],
    bliss: Sequence[tuple], head: Sequence[tuple],
    *, top_k: int,
) -> dict:
    # Orientation: 23 Bliss features x 87 genre (or 56 mood) teacher outputs.
    proposals = []
    nulls = Counter()
    rho_values = []
    for j, name in enumerate(BLISS_COLUMNS):
        left_train = [bliss[i][j] for i in train]
        left_hold = [bliss[i][j] for i in test]
        for k in range(len(head[0])):
            train_y = [head[i][k] for i in train]
            hold_y = [head[i][k] for i in test]
            rho = spearman(left_train, train_y)
            r = pearson(left_train, train_y)
            if rho is None:
                nulls["undefined_spearman_train"] += 1
                continue
            if r is None:
                nulls["undefined_pearson_train"] += 1
            else:
                rho_values.append(abs(rho))
            proposals.append({
                "bliss_feature": name,
                "teacher_class_index": k,
                "train_spearman": rho,
                "train_pearson": r,
                "holdout_spearman": spearman(left_hold, hold_y),
                "holdout_pearson": pearson(left_hold, hold_y),
            })
    # Rank on TRAIN only; never select features using the held-out labels.
    proposals.sort(key=lambda p: (
        -abs(p["train_spearman"]),
        p["bliss_feature"], p["teacher_class_index"],
    ))
    return {
        "possible_feature_teacher_pairs": len(BLISS_COLUMNS) * len(head[0]),
        "estimable_train_spearman_pairs": len(proposals),
        "undefined_train_spearman_pairs": nulls["undefined_spearman_train"],
        "undefined_train_pearson_pairs": nulls["undefined_pearson_train"],
        "median_abs_train_spearman": (
            median(abs(p["train_spearman"]) for p in proposals)
            if proposals else None
        ),
        "strongest_training_selected_pairs": proposals[:top_k],
        "selection_policy": "absolute_train_spearman_desc_only_holdout_not_searched",
        "multiple_comparisons_adjusted": False,
        "significance_claim": False,
    }


def relationship_report(
    rows: Sequence[Mapping], *, seed: int = 20261029,
    test_fraction: float = 0.25, top_k: int = 5,
    min_partition: int = MIN_PARTITION,
) -> dict:
    if (not isinstance(rows, (list, tuple)) or not 8 <= len(rows) <= MAX_RECORDINGS):
        raise ValueError("Need 8..4000 paired, identified, permissioned recordings")
    if type(top_k) is not int or not 0 <= top_k <= 10:
        raise ValueError("Research output is limited to at most ten selected feature pairs")
    if type(min_partition) is not int or min_partition < MIN_PARTITION:
        raise ValueError("Too few independent songs per split")
    features = [_vector(row, "bliss", 23) for row in rows]
    heads = {name: [_vector(row, name, dims) for row in rows]
             for name, dims in HEAD_DIMS.items()}
    part = grouped_partition(rows, seed=seed, test_fraction=test_fraction)
    if min(len(part.train), len(part.holdout)) < min_partition:
        raise ValueError("Artist/album-disjoint partition has too few recordings")
    result = {
        "schema": "bliss_essentia_grouped_teacher_correlations_v1",
        "status": "EXPLORATORY_TEACHER_ASSOCIATION_NOT_SIMILARITY_VALIDATION",
        "train_song_count": len(part.train),
        "holdout_song_count": len(part.holdout),
        "group_components": part.connected_groups,
        "achieved_holdout_fraction": part.achieved_holdout_fraction,
        "relations": {},
        "guarantees": {
            "artist_album_recording_group_disjoint": True,
            "top_pairs_selected_only_on_training_partition": True,
            "no_fitted_transform_or_personal_learner": True,
            "no_individual_song_vectors_names_ids_or_hashes": True,
            "essentia_heads_are_imperfect_teacher_outputs": True,
            "teacher_reconstruction_is_not_musical_similarity_gain": True,
            "no_source_dataset_or_teacher_training_leakage_certified": True,
        }
    }
    for name, head in heads.items():
        result["relations"][name] = _summary(
            rows, part.train, part.holdout, features, head, top_k=top_k
        )
    return result
