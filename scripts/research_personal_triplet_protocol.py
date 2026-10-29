#!/usr/bin/env python3
"""WP2-P1 protocol: held-out Bliss triplet baseline and legacy 23D matrix math.

No model FITTING here: source chrober/bliss-learner is reused for the matrix
format and Mahalanobis formula. A supplied matrix requires an explicit
train-partition attestation; this alone does NOT certify its actual provenance.
The original user's 12 rated PAIRS are not training TRIPLETS.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from general_personal_blend_contract import inspect_legacy_bliss_matrix
from research_grouped_split import grouped_triplet_partition


def frozen_matrix(data: object) -> tuple[tuple[float, ...], ...]:
    if not inspect_legacy_bliss_matrix(data)["structurally_compatible"]:
        raise ValueError("Not a compatible legacy Bliss 23D matrix")
    values = data["m"]["data"]
    n = 23
    matrix = tuple(tuple(float(values[i*n+j]) for j in range(n)) for i in range(n))
    scale = max(1.0, max(abs(v) for row in matrix for v in row))
    tol = 1e-8 * scale
    # The existing learner constructs M = L @ L.T; negative eigenvalues or
    # asymmetric/corrupted stored matrices must not enter scoring.
    for i in range(n):
        for j in range(i):
            if abs(matrix[i][j]-matrix[j][i]) > tol:
                raise ValueError("Learned Bliss matrix is not symmetric")
    lower = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            residual = matrix[i][j] - math.fsum(
                lower[i][k]*lower[j][k] for k in range(j)
            )
            if i == j:
                if residual < -tol:
                    raise ValueError("Learned Bliss matrix is not positive semidefinite")
                lower[i][j] = math.sqrt(max(0.0, residual))
            elif lower[j][j] > math.sqrt(tol):
                lower[i][j] = residual/lower[j][j]
            elif abs(residual) > tol:
                raise ValueError("Learned Bliss matrix violates semidefinite constraint")
    return matrix


def _features(value: object) -> tuple[float, ...]:
    if (not isinstance(value, (tuple, list)) or len(value) != 23
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError("Incomplete, nonnumeric or nonfinite Bliss 23D features")
    return tuple(float(x) for x in value)


def distance(a: Sequence[float], b: Sequence[float],
             matrix: tuple[tuple[float, ...], ...] | None = None) -> float:
    left, right = _features(a), _features(b)
    delta = [x-y for x,y in zip(left,right)]
    if matrix is None:
        return math.sqrt(math.fsum(x*x for x in delta))
    squared = math.fsum(
        delta[i]*matrix[i][j]*delta[j] for i in range(23) for j in range(23)
    )
    if squared < -1e-8 * max(1.0, math.fsum(v*v for v in delta)):
        raise ValueError("Indefinite metric distance")
    return math.sqrt(max(0.0, squared))


def _score_heldout(triplets, features, indices, matrix) -> dict:
    correct = ties = 0
    for i in indices:
        similar_a, similar_b, odd = triplets[i]
        x, y, z = (features[k] for k in (similar_a, similar_b, odd))
        short = distance(x,y,matrix)
        longer_1 = distance(x,z,matrix)
        longer_2 = distance(y,z,matrix)
        if short < min(longer_1, longer_2):
            correct += 1
        elif (short == longer_1 or short == longer_2
              or longer_1 == longer_2):
            ties += 1
    return {
        "correct": correct,
        "ties_or_ambiguous_distance": ties,
        "incorrect_including_ties": len(indices)-correct,
        "scorable_triplets": len(indices),
        "accuracy_including_ties_as_incorrect": correct/len(indices),
    }


def study(
    triplets: Sequence[Sequence[str]], song_features: Mapping[str, Sequence[float]],
    song_metadata: Mapping[str, Mapping], *,
    seed: int = 20261029, test_fraction: float = 0.25,
    legacy_matrix: object | None = None,
    declared_training_triplet_indices: Sequence[int] | None = None,
) -> dict:
    partition = grouped_triplet_partition(
        triplets, song_metadata, seed=seed, test_fraction=test_fraction
    )
    used = {k for triple in triplets for k in triple}
    if any(k not in song_features for k in used):
        raise ValueError("At least one selected track is missing Bliss 23D values")
    features = {key: _features(song_features[key]) for key in used}
    outputs = {
        "schema": "bliss_grouped_personal_triplet_baselines_v1",
        "status": "EXPLORATORY_EVALUATION_PROTOCOL_NOT_PERSONAL_LIFT",
        "train_triplets": partition["train_triplet_count"],
        "holdout_triplets": partition["holdout_triplet_count"],
        "connected_groups": partition["group_component_count"],
        "baseline_raw_23d_euclidean": _score_heldout(
            triplets, features, partition["holdout_triplet_indices"], None
        ),
        "legacy_learned_matrix": None,
        "guarantees": {
            "song_artist_album_recording_and_triplet_family_disjoint": True,
            "training_label_source_independence_not_certified": True,
            "legacy_model_training_artifact_hash_not_independently_verified": True,
            "original_12_user_rated_pairs_not_used": True,
            "source_bliss_feature_scale_not_calibrated": True,
            "not_a_replacement_for_calibrated_general_personal_blend": True,
        },
    }
    if legacy_matrix is not None:
        # The existing learner currently splits and retrains on all triplets;
        # using a matrix trained on the entire survey here would leak holdout
        # votes. Enforce evidence from a separately partition-aware trainer.
        if (declared_training_triplet_indices is None
                or tuple(sorted(declared_training_triplet_indices))
                != partition["train_triplet_indices"]):
            raise ValueError("Legacy matrix must be attested trained on exact held-in triplets only")
        mat = frozen_matrix(legacy_matrix)
        outputs["legacy_learned_matrix"] = _score_heldout(
            triplets, features, partition["holdout_triplet_indices"], mat
        )
        outputs["status"] = "DESCRIPTIVE_LEGACY_MATRIX_NOT_INDEPENDENTLY_CERTIFIED"
    elif declared_training_triplet_indices is not None:
        raise ValueError("Do not attach training evidence without a trained matrix")
    # Never return song IDs, label triples, vectors, or model matrix.
    return outputs
