#!/usr/bin/env python3
"""WP3-R2: evaluate a Bliss-only student embedding against Essentia geometry.

Fit a 23D -> selected teacher-head Ridge transform on grouped TRAIN only.
Holdout sees ONLY the 23 Bliss features at student inference, while the
Essentia teacher scores are heldout reference targets for RESEARCH evaluation.
No musical-label quality claims, pairwise observations share songs.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from research_bliss_essentia_teacher_models import _requires_sklearn
from research_feature_relationships import _vector, HEAD_DIMS, spearman
from research_grouped_split import grouped_partition

MAX_HOLDOUT_SONGS = 80


def _distances(np, vectors) -> list[float]:
    """Pair distances fixed for same ordered holdout songs; no query calibration."""
    return [
        float(np.linalg.norm(vectors[i]-vectors[j]))
        for i in range(len(vectors)) for j in range(i+1,len(vectors))
    ]


def proxy_geometry_report(
    rows: Sequence[Mapping], *, seed: int = 20261029,
    test_fraction: float = 0.25, ridge_alpha: float = 10.0,
) -> dict:
    if (not isinstance(rows, (tuple,list)) or not 24 <= len(rows) <= 4000
            or type(ridge_alpha) is not float or not math.isfinite(ridge_alpha)
            or ridge_alpha <= 0):
        raise ValueError("Need 24..4000 grouped recordings and fixed positive Ridge regularization")
    np, sklearn, _, _, _, Ridge, _, StandardScaler = _requires_sklearn()
    X=np.asarray([_vector(r,"bliss",23) for r in rows],dtype=np.float64)
    Y={h:np.asarray([_vector(r,h,d) for r in rows],dtype=np.float64)
       for h,d in HEAD_DIMS.items()}
    part=grouped_partition(rows,seed=seed,test_fraction=test_fraction)
    if len(part.train) < 12 or len(part.holdout) < 8:
        raise ValueError("Need 12 train and 8 holdout recordings from disjoint groups")
    train=np.asarray(part.train)
    # Test subset sample fixed from heldout indices using predeclared seed;
    # no influence of teacher output or top-k features on sample selection.
    hold=np.asarray(part.holdout)
    if len(hold) > MAX_HOLDOUT_SONGS:
        random=np.random.default_rng(seed)
        hold=np.asarray(sorted(random.choice(hold,size=MAX_HOLDOUT_SONGS,replace=False)))
    scaler=StandardScaler().fit(X[train])
    train_scaled=scaler.transform(X[train])
    hold_scaled=scaler.transform(X[hold])
    raw=_distances(np,X[hold])
    scaled=_distances(np,hold_scaled)
    out={
        "schema":"bliss_only_teacher_geometry_proxy_v1",
        "status":"UNSUPERVISED_TEACHER_GEOMETRY_PROXY_NOT_MUSICAL_VALIDATION",
        "train_songs":len(train),
        "heldout_songs_for_pairs":len(hold),
        "holdout_unique_unordered_pairs":len(hold)*(len(hold)-1)//2,
        "all_group_disjoint_outer_holdout_songs":len(part.holdout),
        "group_components":part.connected_groups,
        "fixed_ridge_alpha":ridge_alpha,
        "input_at_student_inference":"Bliss_23D_only",
        "teacher_head_needed_at_student_inference":False,
        "methods":{},
        "guarantees":{
            "Ridge_and_Bliss_scaler_fitted_on_train_only":True,
            "no_holdout_selection_using_teacher_values":True,
            "no_fitted_personal_user_preferences":True,
            "negative_control_is_training_teacher_permutation":True,
            "pairs_share_songs_not_independent_samples":True,
            "teacher_similarity_is_not_ground_truth_musical_similarity":True,
            "no_production_model_or_audio_vectors_written":True,
        },
    }
    for head,teacher in Y.items():
        teacher_dist=_distances(np,teacher[hold])
        if max(teacher_dist)-min(teacher_dist) <= 1e-12:
            raise ValueError("Heldout teacher geometry is degenerate")
        model=Ridge(alpha=ridge_alpha)
        model.fit(train_scaled,teacher[train])
        predicted=model.predict(hold_scaled)
        if not np.isfinite(predicted).all():
            raise ValueError("Unstable Bliss-only student projections")
        student_dist=_distances(np,predicted)
        # Fixed negative control: shuffle training teacher rows only,
        # never look at heldout teacher rows during fit.
        rng=np.random.default_rng(seed)
        shuffled=teacher[train][rng.permutation(len(train))]
        negative=Ridge(alpha=ridge_alpha)
        negative.fit(train_scaled,shuffled)
        permuted_dist=_distances(np,negative.predict(hold_scaled))
        out["methods"][head]={
            "head_dimensions":HEAD_DIMS[head],
            "heldout_spearman_teacher_vs_original_bliss_euclidean":
                spearman(teacher_dist,raw),
            "heldout_spearman_teacher_vs_train_standardized_bliss_euclidean":
                spearman(teacher_dist,scaled),
            "heldout_spearman_teacher_vs_bliss_only_ridge_student_euclidean":
                spearman(teacher_dist,student_dist),
            "heldout_spearman_teacher_vs_permuted_teacher_negative_control":
                spearman(teacher_dist,permuted_dist),
            "this_is_teacher_distance_reconstruction_not_human_similarity":True,
        }
    return out
