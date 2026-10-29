#!/usr/bin/env python3
"""WP3-R2: group-disjoint Bliss -> Essentia teacher modeling with sklearn.

Uses mature StandardScaler / Ridge / PLSRegression / PCA+CCA. All fitting
occurs on TRAIN only; outer holdout is never used for choosing parameters
or features. This is exploratory teacher reconstruction, NOT improved music
similarity or a certified General/Personal metric. No filesystem or network I/O.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from research_feature_relationships import _vector, HEAD_DIMS, MAX_RECORDINGS
from research_grouped_split import grouped_partition


def _requires_sklearn():
    try:
        import numpy as np
        import sklearn
        from sklearn.cross_decomposition import PLSRegression, CCA
        from sklearn.decomposition import PCA
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "WP3-R2 requires numpy and scikit-learn; see frozen research CI"
        ) from exc
    return np, sklearn, PLSRegression, CCA, PCA, Ridge, make_pipeline, StandardScaler


def _mae(np, observed, predicted) -> float:
    if observed.shape != predicted.shape or not np.isfinite(predicted).all():
        raise ValueError("Missing, nonfinite or mismatched teacher predictions")
    return float(np.mean(np.abs(observed-predicted)))


def model_report(
    rows: Sequence[Mapping], *, seed: int = 20261029,
    test_fraction: float = 0.25,
    ridge_alpha: float = 10.0,
    pls_components: int = 2,
    cca_components: int = 1,
) -> dict:
    """Compare fixed-complexity teacher reconstruction, no hyperparameter search.

    CCA is run on training-fitted PCA-reduced views, which limits the rank;
    PCA truncation is NOT a guarantee of statistically independent test
    observations or evidence of canonical-significance. No 1280D head here.
    """
    if not isinstance(rows, (list, tuple)) or not 16 <= len(rows) <= MAX_RECORDINGS:
        raise ValueError("Need 16..4000 permissioned, paired and grouped recordings")
    if (type(seed) is not int
            or type(test_fraction) is not float or not 0 < test_fraction < 1
            or not math.isfinite(test_fraction)):
        raise ValueError("Invalid fixed deterministic split settings")
    if (type(ridge_alpha) is not float or not math.isfinite(ridge_alpha)
            or ridge_alpha <= 0):
        raise ValueError("Ridge alpha must be a fixed positive finite float")
    if (type(pls_components) is not int or not 1 <= pls_components <= 3
            or type(cca_components) is not int or not 1 <= cca_components <= 2):
        raise ValueError("Unexpected fixed low-dimensional component setting")

    np, sk, PLSRegression, CCA, PCA, Ridge, make_pipeline, StandardScaler = _requires_sklearn()
    X = np.asarray([_vector(r,"bliss",23) for r in rows], dtype=np.float64)
    heads = {head: np.asarray([_vector(r,head,dims) for r in rows],dtype=np.float64)
             for head,dims in HEAD_DIMS.items()}
    part = grouped_partition(rows, seed=seed, test_fraction=test_fraction)
    if min(len(part.train),len(part.holdout)) < 6:
        raise ValueError("At least six disjoint-group recordings needed on each side")
    train,test = np.asarray(part.train),np.asarray(part.holdout)
    Xtr,Xte=X[train],X[test]
    X_rank=int(np.linalg.matrix_rank(Xtr-np.mean(Xtr,axis=0)))
    if X_rank < pls_components or X_rank < cca_components:
        raise ValueError("Insufficient independent Bliss variation for fixed model complexity")

    report={
        "schema":"bliss_essentia_grouped_regularized_teacher_models_v1",
        "status":"EXPLORATORY_TEACHER_RECONSTRUCTION_NOT_MUSICAL_SIMILARITY",
        "train_songs":len(train),
        "holdout_songs":len(test),
        "connected_group_count":part.connected_groups,
        "achieved_holdout_fraction":part.achieved_holdout_fraction,
        "environment":{
            "numpy":np.__version__,
            "scikit_learn":sk.__version__,
        },
        "fixed_hyperparameters":{
            "ridge_alpha":ridge_alpha,
            "pls_components":pls_components,
            "cca_components":cca_components,
            "cca_view_pca_dimensions_max":3,
        },
        "methods":{},
        "guarantees":{
            "group_disjoint_train_holdout":True,
            "fit_scaler_ridge_pls_pca_cca_only_on_train":True,
            "no_outer_holdout_hyperparameter_search":True,
            "no_source_or_song_ids_in_report":True,
            "teacher_outputs_are_not_ground_truth":True,
            "musical_similarity_not_assessed":True,
            "artist_album_source_attribution_may_be_incomplete":True,
            "upstream_teacher_training_overlap_not_certified":True,
        }
    }
    for head,Y in heads.items():
        Ytr,Yte=Y[train],Y[test]
        # Fit baseline solely on TRAIN targets, never on unseen teacher values.
        teacher_mean=np.mean(Ytr,axis=0,keepdims=True)
        baseline=np.broadcast_to(teacher_mean,Yte.shape)
        baseline_mae=_mae(np,Yte,baseline)
        ridge=make_pipeline(StandardScaler(), Ridge(alpha=ridge_alpha))
        ridge.fit(Xtr,Ytr)
        ridge_mae=_mae(np,Yte,ridge.predict(Xte))
        pls=make_pipeline(StandardScaler(),PLSRegression(
            n_components=pls_components,max_iter=500,scale=True
        ))
        pls.fit(Xtr,Ytr)
        pls_mae=_mae(np,Yte,pls.predict(Xte))
        # Rank-truncate both views on TRAIN only. CCA is not supervised
        # teacher reconstruction, so report heldout canonical covariance
        # association separately from ridge/PLS prediction.
        y_rank=int(np.linalg.matrix_rank(Ytr-np.mean(Ytr,axis=0)))
        if y_rank < cca_components:
            raise ValueError("Insufficient independent teacher-head rank")
        view_dims=min(3,X_rank,y_rank,len(train)-2)
        if view_dims < cca_components:
            raise ValueError("Insufficient rank for frozen CCA")
        xp=make_pipeline(StandardScaler(),PCA(n_components=view_dims,svd_solver="full"))
        yp=make_pipeline(StandardScaler(),PCA(n_components=view_dims,svd_solver="full"))
        xt=xp.fit_transform(Xtr)
        yt=yp.fit_transform(Ytr)
        canonical=CCA(n_components=cca_components,max_iter=500,scale=True)
        canonical.fit(xt,yt)
        xtest, ytest=canonical.transform(xp.transform(Xte),yp.transform(Yte))
        associations=[]
        for component in range(cca_components):
            a,b=xtest[:,component],ytest[:,component]
            aa=a-a.mean()
            bb=b-b.mean()
            var=float(np.dot(aa,aa)*np.dot(bb,bb))
            corr=None if var <= 1e-20 else float(
                np.clip(np.dot(aa,bb)/math.sqrt(var),-1,1)
            )
            associations.append(corr)
        report["methods"][head]={
            "teacher_dimensions":HEAD_DIMS[head],
            "constant_predictor_train_mean_mae":baseline_mae,
            "ridge_train_only_holdout_mae":ridge_mae,
            "pls_train_only_holdout_mae":pls_mae,
            "ridge_mae_reduction_vs_train_mean":baseline_mae-ridge_mae,
            "pls_mae_reduction_vs_train_mean":baseline_mae-pls_mae,
            "cca_pca_dimensionality":view_dims,
            "cca_heldout_canonical_pearson":associations,
            "not_independent_musical_quality":True,
        }
    return report
