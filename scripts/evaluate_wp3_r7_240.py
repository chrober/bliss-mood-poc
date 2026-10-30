#!/usr/bin/env python3
"""WP3-R7: post-R6 exploratory robustness and teacher-neighbor retrieval.

R6 240-song cohort REUSED, not an untouched confirmation set.
No new scans, teacher-label fitting, metric selection or human-quality claims.
Only aggregate numbers are emitted; source keys and vectors remain private.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys

import evaluate_wp3_r6_240 as r6
from research_bliss_essentia_teacher_models import _requires_sklearn
from prepare_wp3_blinded_bliss_student_pilot import _old_grouped_rows, _load_new_bliss
from wp3_r6_native_240 import _private_json

SCHEMA = "wp3-r7-post-r6-song-bootstrap-retrieval-v1"
SEED = 20261030
BOOTSTRAPS = 300
KS = (5, 10, 20)


def _assert_same(actual, recorded, path="root"):
    """Pinned R6 numerical + provenance reproduction; never accept drift."""
    if isinstance(actual, dict) and isinstance(recorded, dict):
        if set(actual) != set(recorded):
            raise ValueError("R6 report keys have changed")
        for key in actual:
            _assert_same(actual[key], recorded[key], path + "." + key)
    elif type(actual) in (float, int) and type(recorded) in (float, int):
        if not math.isclose(actual, recorded, rel_tol=1e-8, abs_tol=1e-10):
            raise ValueError("R6 numerical reproduction differs")
    elif actual != recorded:
        raise ValueError("R6 frozen report provenance differs")


def _validate_singleton_groups(manifest):
    """Every new track represents a distinct known artist/album/recording group."""
    songs = manifest.get("selected_songs")
    if not isinstance(songs, list) or len(songs) != r6.N:
        raise ValueError("R5 cohort is not 240 separate source identities")
    artists, albums, recordings = set(), set(), set()
    for song in songs:
        credits = song.get("artist_keys")
        album = song.get("lms_album_id")
        rec = song.get("recording_mbid")
        if (not isinstance(credits, list) or not credits
                or any(not isinstance(x, str) or not x.strip() for x in credits)
                or len(set(credits)) != len(credits)
                or album is None or not isinstance(rec, str) or not rec.strip()):
            raise ValueError("R5 group metadata incomplete")
        if (artists.intersection(credits) or album in albums or rec in recordings):
            raise ValueError("Shared artist/album/recording group: bootstrap invalid")
        artists.update(credits)
        albums.add(album)
        recordings.add(rec)


def _distance_matrices(np, Xnew, Xtrain, Yold, Yold_genre, Ymood, Ygenre, emb):
    from scipy.spatial.distance import cdist
    _, _, PLSRegression, _, _, Ridge, make_pipeline, StandardScaler = _requires_sklearn()
    scaler = StandardScaler().fit(Xtrain)
    student = Ridge(alpha=10.0).fit(scaler.transform(Xtrain), Yold)
    genre_pls = make_pipeline(StandardScaler(),
                             PLSRegression(n_components=2, max_iter=500, scale=True))
    genre_pls.fit(Xtrain, Yold_genre)
    def euclidean(x):
        d = cdist(np.asarray(x, dtype=np.float64),
                  np.asarray(x, dtype=np.float64), metric="euclidean")
        np.fill_diagonal(d, 0.0)
        return d
    def cosine(x, center=None):
        v = np.asarray(x, dtype=np.float64)
        if center is not None:
            v = v - center
        norms = np.linalg.norm(v, axis=1)
        if not np.isfinite(norms).all() or (norms < 1e-12).any():
            raise ValueError("Degenerate R7 cosine view")
        unit = v / norms[:, None]
        d = 1.0 - unit @ unit.T
        np.fill_diagonal(d, 0.0)
        return d
    return {
        "raw_bliss23_euclidean": euclidean(Xnew),
        "old_train_scaled_bliss23_euclidean": euclidean(scaler.transform(Xnew)),
        "frozen_moodtheme_ridge_student_euclidean": euclidean(
            student.predict(scaler.transform(Xnew))),
        "frozen_genre_pls2_student_euclidean": euclidean(genre_pls.predict(Xnew)),
        "genre87_cosine_dissimilarity": cosine(Ygenre),
        "moodtheme56_cosine_dissimilarity": cosine(Ymood),
        "moodtheme56_old_train_mean_centered_cosine_dissimilarity": cosine(
            Ymood, center=np.mean(Yold, axis=0)),
        "discogs_effnet_embedding1280_cosine_dissimilarity": cosine(emb),
        "_teacher_mood_euclidean": euclidean(Ymood),
        "_teacher_genre_euclidean": euclidean(Ygenre),
    }


def _rho(np, a, b):
    from scipy.stats import spearmanr
    value = float(spearmanr(a, b).statistic)
    if not math.isfinite(value):
        raise ValueError("Undefined R7 pairwise rank association")
    return value


def _bootstrap_delta(np, baseline, candidate, teacher, *,
                     repetitions=BOOTSTRAPS, seed=SEED):
    """Resample whole songs; exclude duplicate-self comparisons.

    Repeated song-group draws reweight distinct *source* pairs together;
    treating 28,680 pairs as IID would underestimate uncertainty.
    """
    n = len(baseline)
    if (n < 24 or baseline.shape != (n, n)
            or candidate.shape != (n, n) or teacher.shape != (n, n)
            or repetitions < 50):
        raise ValueError("Bootstrap requires matching complete song matrices")
    rng = np.random.default_rng(seed)
    upper = np.triu_indices(n, 1)
    delta = []
    for _ in range(repetitions):
        draw = rng.integers(n, size=n)
        left, right = draw[upper[0]], draw[upper[1]]
        keep = left != right
        x, y = left[keep], right[keep]
        delta.append(_rho(np, candidate[x, y], teacher[x, y])
                     - _rho(np, baseline[x, y], teacher[x, y]))
    low, high = np.percentile(delta, [2.5, 97.5])
    return {"bootstrap_samples": repetitions,
            "seed": seed,
            "percentile_95_interval": [float(low), float(high)],
            "method": "paired_song_group_bootstrap_excluding_same_source_pairs",
            "confirmatory_significance_test": False}


def _retrieval(np, candidate, teacher, ks=KS):
    n = len(candidate)
    if n <= max(ks) or candidate.shape != (n, n) or teacher.shape != (n, n):
        raise ValueError("Invalid song-neighbor evaluation matrices")
    c = np.asarray(candidate, dtype=np.float64).copy()
    t = np.asarray(teacher, dtype=np.float64).copy()
    if not np.isfinite(c).all() or not np.isfinite(t).all():
        raise ValueError("Nonfinite distances")
    np.fill_diagonal(c, np.inf)
    np.fill_diagonal(t, np.inf)
    ci = np.argsort(c, axis=1, kind="stable")
    ti = np.argsort(t, axis=1, kind="stable")
    return {f"top_{k}_mean_teacher_neighbor_overlap": float(np.mean([
        len(set(ci[i, :k]) & set(ti[i, :k])) / k for i in range(n)
    ])) for k in ks}


def evaluate(plan_dir: Path, old_db: Path, bliss_db: Path, manifest_path: Path,
             protocol_path: Path, r6_report_path: Path) -> dict:
    # Re-run complete R6 source/model/frozen-protocol gates, compare with
    # the original stored R6 result, and do not overwrite that result.
    confirmed = r6.evaluate(plan_dir, old_db, bliss_db, manifest_path, protocol_path)
    original = _private_json(r6_report_path)
    _assert_same(confirmed, original)
    manifest = _private_json(manifest_path)
    _validate_singleton_groups(manifest)
    old, _ = _old_grouped_rows(old_db)
    keys, new_bliss = _load_new_bliss(bliss_db, manifest, {row[0] for row in old})
    native = r6._native_rows(plan_dir / "native-features.sqlite", keys,
                              _private_json(plan_dir / "private-scan-plan.json"))
    np, _, _, _, _, _, _, _ = _requires_sklearn()
    Xtrain = np.asarray([r[1] for r in old], dtype=np.float64)
    Ytrain = np.asarray([r[2] for r in old], dtype=np.float64)
    Xnew = np.asarray(new_bliss, dtype=np.float64)
    Ymood = np.asarray([native[k]["moodtheme"] for k in keys], dtype=np.float64)
    Ygenre = np.asarray([native[k]["genre"] for k in keys], dtype=np.float64)
    emb = np.asarray([native[k]["embedding"] for k in keys], dtype=np.float64)
    genres = []
    with closing(sqlite3.connect(old_db.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        for key, blob in db.execute(
                "SELECT track_key, genre_f32_le FROM paired_tracks "
                "ORDER BY track_key COLLATE BINARY"):
            if key != old[len(genres)][0] or not isinstance(blob, bytes) or len(blob) != 348:
                raise ValueError("Old Genre87 train order mismatch")
            genres.append(struct.unpack("<87f", blob))
    if len(genres) != 100 or len(keys) != 240:
        raise ValueError("Old/new feature dimensions changed")
    matrices = _distance_matrices(np, Xnew, Xtrain, Ytrain,
                                  np.asarray(genres, dtype=np.float64),
                                  Ymood, Ygenre, emb)
    teachers = {"mood": matrices.pop("_teacher_mood_euclidean"),
                "genre": matrices.pop("_teacher_genre_euclidean")}
    triu = np.triu_indices(240, 1)
    rhos = {
        name: {kind: _rho(np, d[triu], teacher[triu])
               for kind, teacher in teachers.items()}
        for name, d in matrices.items()
    }
    for name, values in confirmed["pairwise_spearman_to_teachers"].items():
        for kind, value in (("mood", values["vs_moodteacher_euclidean"]),
                            ("genre", values["vs_genreteacher_euclidean"])):
            if abs(rhos[name][kind] - value) > 1e-8:
                raise ValueError("R7 distances do not reproduce frozen R6 Spearman")
    raw = matrices["raw_bliss23_euclidean"]
    ridge = matrices["frozen_moodtheme_ridge_student_euclidean"]
    pls = matrices["frozen_genre_pls2_student_euclidean"]
    comparisons = {}
    for key, candidate, teacher in (
            ("mood_ridge_minus_raw", ridge, teachers["mood"]),
            ("genre_ridge_minus_raw", ridge, teachers["genre"]),
            ("genre_pls2_minus_raw", pls, teachers["genre"])):
        kind = "mood" if key.startswith("mood") else "genre"
        candname = ("frozen_genre_pls2_student_euclidean"
                    if "pls2" in key else "frozen_moodtheme_ridge_student_euclidean")
        comparisons[key] = {
            "raw_spearman": rhos["raw_bliss23_euclidean"][kind],
            "candidate_spearman": rhos[candname][kind],
            "delta_spearman": rhos[candname][kind] -
                              rhos["raw_bliss23_euclidean"][kind],
            "uncertainty": _bootstrap_delta(np, raw, candidate, teacher)
        }
    retrieval = {
        name: {kind: _retrieval(np, d, t)
               for kind, t in teachers.items()}
        for name, d in matrices.items()
    }
    return {
        "schema": SCHEMA,
        "status": "POST_R6_EXPLORATORY_TEACHER_PROXY_NOT_INDEPENDENT_OR_HUMAN_VALIDATION",
        "cohort_songs": 240, "source_identity_groups": 240,
        "dependent_unordered_pairs": 28680,
        "r6_report_exactly_reproduced": True,
        "r6_240_cohort_already_inspected_before_r7": True,
        "bootstrap_unit": "R5_metadata_separate_artist_album_recording_song_groups",
        "bootstrap_repetitions": BOOTSTRAPS, "bootstrap_seed": SEED,
        "teacher_distance_spearman": rhos,
        "paired_bootstrap_differences": comparisons,
        "teacher_top_k_retrieval": retrieval,
        "retrieval_catalog": "same_240_songs_excluding_query_itself",
        "top_k_retrieval_uncertainty_calculated": False,
        "model_fitted_only_on_previous_100": True,
        "new_teacher_used_for_fit_or_hyperparameters": False,
        "human_perceptual_similarity_measured": False,
        "multiple_comparison_corrected_or_preregistered_after_r6": False,
        "production_metric_or_personal_model_selected": False,
        "private_song_identifiers_or_vectors_in_aggregate": False
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("plan-dir", "old-grouped-research-db", "bliss-db",
                 "r5-manifest", "frozen-protocol", "r6-report", "out"):
        p.add_argument("--" + flag, required=True, type=Path)
    args = vars(p.parse_args())
    dest = args.pop("out")
    try:
        if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
            raise ValueError("R7 output must be a new private report")
        report = evaluate(args["plan_dir"], args["old_grouped_research_db"],
                          args["bliss_db"], args["r5_manifest"],
                          args["frozen_protocol"], args["r6_report"])
        with dest.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2, allow_nan=False)
            f.write("\n")
        print(json.dumps({"schema": SCHEMA, "status": report["status"],
              "songs": 240, "source_groups": 240,
              "teacher_proxy_aggregate_saved_private": True,
              "human_validation": False}, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, sqlite3.Error):
        p.exit(2, "WP3 R7 BLOCKED: frozen inputs, report, identities, "
               "vectors or numerical evaluation invalid; no quality claim\n")


if __name__ == "__main__":
    sys.exit(main())
