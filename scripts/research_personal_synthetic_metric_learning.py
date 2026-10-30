#!/usr/bin/env python3
"""WP2-P3: fully synthetic, source-group-held-out personal triplet learning.

Compare raw Bliss23 Euclidean, regularized diagonal and diagonal+rank-2
positive-definite Mahalanobis geometries. ALL data and labels are fictional.
No user preferences, audio, model downloads, feature DBs, profile records
or actual calibration certification. Historical Bliss Rust learner is not run.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import itertools
import json
import math
from pathlib import Path
import random
import sys

from general_personal_blend_contract import PersonalEvidence, choose_scores
from research_grouped_split import grouped_triplet_partition
from research_personal_triplet_protocol import frozen_matrix, distance

DIM = 23
SEED = 20261030
GROUPS = 48
SONGS_PER_GROUP = 6
TRIPLETS_PER_GROUP = 8
CHECKPOINTS = (0, 10, 25, 50, 100)
EPOCHS = 28
LEARNING_RATE = 0.12
MARGIN = 0.07
PRIOR_STRENGTH = 0.0015
FACTOR_RANK = 2
REPORT_SCHEMA = "wp2-p3-fictional-grouped-diagonal-rank2-learning-v1"
CAPACITIES = ("diagonal", "diagonal_plus_rank2")


@dataclass(frozen=True)
class Model:
    diagonal: tuple[float, ...]
    factors: tuple[tuple[float, ...], ...] = ()


def _difference(a, b):
    return tuple(x - y for x, y in zip(a, b))


def squared_distance(a, b, model: Model) -> float:
    if len(a) != DIM or len(b) != DIM or len(model.diagonal) != DIM:
        raise ValueError("WP2 synthetic model requires Bliss23 shape")
    if any(len(row) != DIM for row in model.factors):
        raise ValueError("Invalid PSD low-rank factor shape")
    delta = _difference(a, b)
    if (any(not math.isfinite(z) for z in (*a, *b, *model.diagonal))
            or any(not math.isfinite(z) for row in model.factors for z in row)
            or any(z <= 0.0 for z in model.diagonal)):
        raise ValueError("Invalid feature/model values")
    return math.fsum(w * v * v for w, v in zip(model.diagonal, delta)) + math.fsum(
        math.fsum(x * y for x, y in zip(row, delta))**2
        for row in model.factors
    )


def _oracle_weights(scenario: str):
    if scenario not in ("axis_sparse", "cross_feature"):
        raise ValueError("Unknown predeclared fictional scenario")
    # No external or private music attributes: purely fictional target.
    return (8.0, 4.0, 2.0, 1.0) + (0.04,) * (DIM - 4)


def _oracle_d2(a, b, scenario):
    delta = _difference(a, b)
    val = math.fsum(w * x * x
                    for w, x in zip(_oracle_weights(scenario), delta))
    if scenario == "cross_feature":
        val += 15.0 * (delta[4] + delta[5])**2
    return val


def fictional_cohort(seed: int, scenario: str):
    """Fixed fictional 48 x 6 tracks, 8 independent-ish votes per group.

    Song IDs exist only in process; they are never exported. Grouped split
    treats shared artist/album and repeated triplets as one partition.
    """
    rng = random.Random(seed)
    features, metadata, triplets = {}, {}, []
    for g in range(GROUPS):
        ids = [f"fictional-{g:03d}-{j:02d}" for j in range(SONGS_PER_GROUP)]
        for j, key in enumerate(ids):
            features[key] = tuple(rng.gauss(0.0, 1.0) for _ in range(DIM))
            metadata[key] = {
                "artist_group": f"fictional-artist-{g}",
                "album_group": f"fictional-album-{g}",
                "recording_group": f"fictional-recording-{g}-{j}",
            }
        triples = list(itertools.combinations(ids, 3))
        rng.shuffle(triples)
        for triple in triples[:TRIPLETS_PER_GROUP]:
            pairs = [(triple[0], triple[1], triple[2]),
                     (triple[0], triple[2], triple[1]),
                     (triple[1], triple[2], triple[0])]
            sim1, sim2, odd = min(
                pairs,
                key=lambda pair: _oracle_d2(features[pair[0]],
                                            features[pair[1]], scenario)
            )
            triplets.append((sim1, sim2, odd))
    return tuple(triplets), features, metadata


def fit(triplets, features, indices, *, capacity: str, seed: int) -> Model:
    if capacity not in CAPACITIES:
        raise ValueError("Unsupported fixed research model capacity")
    if len(set(indices)) != len(indices) or any(
            type(i) is not int or not 0 <= i < len(triplets) for i in indices):
        raise ValueError("Duplicate/invalid training triplet index")
    weights = [1.0] * DIM
    if not indices:
        return Model(tuple(weights))  # EXACT unpersonalized cold start
    rng = random.Random(seed)
    factors = ([[rng.uniform(-0.035, 0.035) for _ in range(DIM)]
                for _ in range(FACTOR_RANK)]
               if capacity == "diagonal_plus_rank2" else [])
    train_order = list(indices)
    for _epoch in range(EPOCHS):
        rng.shuffle(train_order)
        for i in train_order:
            a, b, odd = triplets[i]
            if any(k not in features for k in (a, b, odd)):
                raise ValueError("Selected train features missing")
            pos = _difference(features[a], features[b])
            for negative in (_difference(features[a], features[odd]),
                             _difference(features[b], features[odd])):
                d_pos = math.fsum(w * x * x for w, x in zip(weights, pos))
                d_neg = math.fsum(w * x * x for w, x in zip(weights, negative))
                proj_pos = [math.fsum(x*y for x,y in zip(row,pos))
                            for row in factors]
                proj_neg = [math.fsum(x*y for x,y in zip(row,negative))
                            for row in factors]
                d_pos += math.fsum(x*x for x in proj_pos)
                d_neg += math.fsum(x*x for x in proj_neg)
                t = max(-50.0, min(50.0, MARGIN + (d_pos - d_neg)/DIM))
                direction = 1.0 / (1.0 + math.exp(-t))
                # Pairwise logistic violation loss; diagonal positivity is
                # projected; rank2 factorisation guarantees PSD for all steps.
                for j in range(DIM):
                    grad = (direction * (pos[j]*pos[j] -
                                         negative[j]*negative[j]) / DIM
                            + PRIOR_STRENGTH*(weights[j]-1.0))
                    weights[j] = max(0.02, min(12.0,
                                              weights[j] - LEARNING_RATE*grad))
                for k, row in enumerate(factors):
                    for j in range(DIM):
                        grad = (direction * 2.0 *
                                (proj_pos[k]*pos[j] - proj_neg[k]*negative[j]) / DIM
                                + PRIOR_STRENGTH*row[j])
                        row[j] = max(-3.0, min(3.0,
                                              row[j] - LEARNING_RATE*0.5*grad))
    return Model(tuple(weights), tuple(tuple(row) for row in factors))


def matrix_as_legacy(model: Model):
    """Use existing PSD / 23x23 read-only validation; NO model exported."""
    values = [
        (model.diagonal[i] if i == j else 0.0) +
        math.fsum(row[i]*row[j] for row in model.factors)
        for i in range(DIM) for j in range(DIM)
    ]
    return {"m": {"v": 1, "dim": [DIM, DIM], "data": values}}


def heldout_score(triplets, features, indices, model: Model):
    if not indices:
        raise ValueError("Cannot score empty group-held-out sample")
    correct = ambiguous = 0
    for i in indices:
        a, b, odd = triplets[i]
        x, y, z = features[a], features[b], features[odd]
        positive = squared_distance(x, y, model)
        neg_a = squared_distance(x, z, model)
        neg_b = squared_distance(y, z, model)
        if positive + 1e-12 < min(neg_a, neg_b):
            correct += 1
        elif min(abs(positive-neg_a), abs(positive-neg_b),
                 abs(neg_a-neg_b)) <= 1e-12:
            ambiguous += 1
    return {
        "correct": correct, "denominator": len(indices),
        "ambiguous": ambiguous,
        "accuracy_with_ambiguous_as_incorrect": correct / len(indices),
    }


def synthetic_blend_gate():
    """Exercise existing full-query compatibility; no real calibration claim."""
    general = (0.15, 0.45, 0.85)
    personal_scores = (0.80, 0.60, 0.10)
    args = {
        "expected_profile": "fictional-profile",
        "expected_feature_fingerprint": "fictional-feature-v1",
        "expected_score_calibration_id": "stipulated-fictional-common-scale",
        "expected_candidate_cohort_fingerprint": "fictional-query",
    }
    # True flags SIMULATE already independently passed gates, which the
    # experiment itself NEVER establishes for real user models or scorers.
    simulated = PersonalEvidence(
        profile_id=args["expected_profile"],
        feature_fingerprint=args["expected_feature_fingerprint"],
        score_calibration_id=args["expected_score_calibration_id"],
        candidate_cohort_fingerprint=args["expected_candidate_cohort_fingerprint"],
        version=1, quality_validated=True, calibration_validated=True,
        scores=personal_scores,
    )
    results = {}
    for p in (0, 25, 50, 75, 100):
        result = choose_scores(general, requested_personal_percent=p,
                               personal=simulated, **args)
        expected = tuple((1-p/100)*g + p/100*s
                         for g, s in zip(general, personal_scores))
        if any(abs(x-y) > 1e-14 for x,y in zip(result.scores, expected)):
            raise AssertionError("Blend contract mismatches fixed simulated scores")
        missing = choose_scores(general, requested_personal_percent=p,
                                personal=None, **args)
        incompatible = choose_scores(general, requested_personal_percent=p,
            personal=PersonalEvidence(
                profile_id=simulated.profile_id,
                feature_fingerprint=simulated.feature_fingerprint,
                score_calibration_id=simulated.score_calibration_id,
                candidate_cohort_fingerprint=simulated.candidate_cohort_fingerprint,
                version=1, quality_validated=False, calibration_validated=False,
                scores=personal_scores),
            **args)
        if (missing.scores != general or incompatible.scores != general
                or missing.effective_personal_percent != 0
                or incompatible.effective_personal_percent != 0):
            raise AssertionError("Personal incompatibility lost General fallback")
        results[str(p)] = {
            "simulation_valid_model_effective_percent":
                result.effective_personal_percent,
            "missing_or_uncertified_model_effective_percent": 0,
            "full_query_fallback_verified": True,
        }
    return {
        "assumed_prevalidated_personal_model_is_fictional": True,
        "independent_real_score_calibration_demonstrated": False,
        "five_settings_tested": results,
        "production_model_eligible_for_activation": False,
    }


def run(seed: int = SEED):
    out = {}
    for scenario in ("axis_sparse", "cross_feature"):
        triplets, features, metadata = fictional_cohort(seed, scenario)
        split = grouped_triplet_partition(
            triplets, metadata, seed=seed, test_fraction=0.25)
        train, test = split["train_triplet_indices"], split["holdout_triplet_indices"]
        # Freeze training order without consulting held-out feature/labels.
        sample_order = list(train)
        random.Random(seed+1).shuffle(sample_order)
        baseline = Model((1.0,) * DIM)
        series = {}
        for n in CHECKPOINTS:
            selected = tuple(sample_order[:n])
            if len(selected) != n:
                raise ValueError("Not enough grouped train-only triplets")
            methods = {"raw_bliss23_euclidean": heldout_score(
                triplets, features, test, baseline)}
            for capacity in CAPACITIES:
                fitted = fit(triplets, features, selected,
                             capacity=capacity, seed=seed+3)
                # Cross-check 23x23 materialization against the existing
                # legacy PSD geometry validator, not a Rust learner parity claim.
                validated = frozen_matrix(matrix_as_legacy(fitted))
                x, y = features[triplets[test[0]][0]], features[triplets[test[0]][1]]
                if not math.isclose(math.sqrt(squared_distance(x,y,fitted)),
                                    distance(x,y,validated),
                                    abs_tol=1e-8, rel_tol=1e-8):
                    raise AssertionError("Synthetic PSD matrix scorer parity failed")
                methods[capacity] = heldout_score(
                    triplets, features, test, fitted)
            series[str(n)] = methods
        out[scenario] = {
            "fictional_song_count": len(features),
            "fictional_question_count": len(triplets),
            "connected_identity_groups": split["group_component_count"],
            "train_question_count": len(train),
            "holdout_question_count": len(test),
            "train_holdout_artist_album_recording_and_triplet_disjoint": True,
            "learning_curve_train_question_counts": list(CHECKPOINTS),
            "frozen_train_only_learning_curve": series,
        }
    return {
        "schema": REPORT_SCHEMA,
        "status": "SYNTHETIC_ONLY_NO_MEASURED_MUSICAL_PERSONAL_IMPROVEMENT",
        "seed": seed, "bliss_dimension": DIM,
        "models": ["raw_bliss23_euclidean", *CAPACITIES],
        "low_rank_factor_count": FACTOR_RANK,
        "optimizer": "fixed_projected_pairwise_logistic_SGD_prior_regularized",
        "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
        "scenarios": out,
        "blend_contract_simulation": synthetic_blend_gate(),
        "existing_rust_bliss_learner_executed": False,
        "real_human_votes_or_audio_used": False,
        "feature_representations_calibrated_on_real_music": False,
        "general_metric_selected": False,
        "personal_model_validated_or_deployed": False,
        "private_song_id_feature_or_weight_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = run()
    if args.out is not None:
        if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
            parser.error("Cannot overwrite or create output directory")
        with args.out.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
            f.write("\n")
    print(json.dumps({
        "schema": result["schema"], "status": result["status"],
        "fictional_scenarios": list(result["scenarios"]),
        "full_query_fallback": True, "real_personal_lift": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
