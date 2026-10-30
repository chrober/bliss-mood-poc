#!/usr/bin/env python3
"""WP3 sensitivity and redundancy of SELECTED-ON-SAME-DATA Bliss/Essentia signals.

Read ONLY the existing private research SQLite. This is descriptive robustness
WITHIN the original cohort, not an artist/album holdout, bootstrap confidence
interval, external replication, teacher fitting, or improved song similarity.
No raw songs, vectors, file paths, hashes or inferred groups leave the DB.
Python stdlib only, compatible with the selected Python 3.15.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sqlite3
import statistics
import sys

from analyze_wp3_snapshot_correlations import _read, _pearson, _midranks
from audit_bliss_essentia_join import BLISS_COLUMNS

REPORT_SCHEMA = "wp3-bliss-essentia-within-cohort-stability-v1"
# Frozen from the eight most extreme pairs of EACH head in the user's
# 30-Oct-2026 descriptive 100-song report. Selection was post hoc.
# No pair is "pre-registered" or independently validated by this reanalysis.
SELECTED = {
    "genre": (
        ("Chroma6", "metal"),
        ("Chroma6", "hard"),
        ("Chroma12", "metal"),
        ("Chroma12", "hard"),
        ("Chroma13", "metal"),
        ("MeanSpectralFlatness", "hard"),
        ("Chroma11", "easylistening"),
        ("Chroma13", "improvisation"),
    ),
    "moodtheme": (
        ("Chroma12", "soft"),
        ("Chroma11", "soft"),
        ("Chroma13", "soft"),
        ("Chroma12", "nature"),
        ("Chroma6", "soft"),
        ("Chroma12", "romantic"),
        ("Chroma6", "romantic"),
        ("Chroma11", "romantic"),
    ),
}
FOCUS_BLISS = (
    "Chroma6", "Chroma11", "Chroma12", "Chroma13", "MeanSpectralFlatness"
)
FOCUS_CLASSES = {
    "genre": ("metal", "hard", "easylistening", "improvisation"),
    "moodtheme": ("soft", "romantic", "nature"),
}


def _spearman(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    return _pearson(_midranks(a), _midranks(b))


def _quantile(ordered: list[float], p: float) -> float:
    if not ordered or not 0 <= p <= 1:
        raise ValueError("Invalid quantile arguments")
    at = (len(ordered) - 1) * p
    low = int(at)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] * (high - at) + ordered[high] * (at - low)


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _correlations(columns: dict[str, tuple[float, ...]], pairs: list[tuple[str, str]]) -> list[dict]:
    result = []
    for left, right in pairs:
        result.append({
            "left": left,
            "right": right,
            "spearman_rho": _round(_spearman(columns[left], columns[right])),
        })
    return result


def analyze(db: Path, *, seed: int = 20261030, resamples: int = 200,
            sample_fraction: float = 0.8) -> dict:
    if type(seed) is not int or type(resamples) is not int or not 20 <= resamples <= 500:
        raise ValueError("Sampling seed/replicate count not supported")
    if (type(sample_fraction) is not float or not math.isfinite(sample_fraction)
            or not 0.6 <= sample_fraction <= 0.9):
        raise ValueError("Sample fraction outside a bounded descriptive range")
    bliss, heads, labels, group = _read(db)
    n = len(bliss)
    if n < 24:
        raise ValueError("At least 24 original songs are required for sensitivity checks")
    sample_size = round(n * sample_fraction)
    if sample_size < 12 or sample_size >= n:
        raise ValueError("Subsampling requires at least 12 songs and an omitted subset")

    # Columns are held in private RAM only. Neither vectors nor track IDs
    # enter the report. Missing model classes stop the analysis; no aliases.
    columns = {
        name: tuple(row[i] for row in bliss)
        for i, name in enumerate(BLISS_COLUMNS)
    }
    for head, model_labels in labels.items():
        for j, name in enumerate(model_labels):
            columns[f"{head}:{name}"] = tuple(row[j] for row in heads[head])
    for head, pairs in SELECTED.items():
        if not all(f"{head}:{target}" in columns for _, target in pairs):
            raise ValueError("Frozen, post-selected class missing in this model cohort")

    # Every Bliss feature pair, not merely four chroma components.
    bliss_pairs = [
        (BLISS_COLUMNS[i], BLISS_COLUMNS[j])
        for i in range(len(BLISS_COLUMNS))
        for j in range(i + 1, len(BLISS_COLUMNS))
    ]
    all_bliss = _correlations(columns, bliss_pairs)
    defined = [p for p in all_bliss if p["spearman_rho"] is not None]
    defined.sort(key=lambda p: (-abs(p["spearman_rho"]), p["left"], p["right"]))

    # The finite set of original candidates is explicitly AFTER earlier
    # selection; strong correlations can be an artist/album composition effect.
    rng = random.Random(seed)
    samples = [
        tuple(sorted(rng.sample(range(n), sample_size)))
        for _ in range(resamples)
    ]
    selected = []
    for head, pairs in SELECTED.items():
        for feature, target in pairs:
            left = columns[feature]
            right = columns[f"{head}:{target}"]
            full = _spearman(left, right)
            leave_one_out = []
            for omitted in range(n):
                keep = (i for i in range(n) if i != omitted)
                indices = tuple(keep)
                value = _spearman(
                    tuple(left[i] for i in indices),
                    tuple(right[i] for i in indices)
                )
                if value is not None:
                    leave_one_out.append(value)
            sampled = []
            for indices in samples:
                value = _spearman(
                    tuple(left[i] for i in indices),
                    tuple(right[i] for i in indices)
                )
                if value is not None:
                    sampled.append(value)
            sampled.sort()
            comparison = (sum(
                (value > 0) == (full > 0)
                for value in sampled
            ) / len(sampled) if full is not None and sampled else None)
            selected.append({
                "bliss_feature": feature,
                "essentia_head": head,
                "essentia_class": target,
                "full_pearson_r": _round(_pearson(left, right)),
                "full_spearman_rho": _round(full),
                "leave_one_song_out_max_abs_rho_shift": (
                    _round(max(abs(v - full) for v in leave_one_out))
                    if full is not None and leave_one_out else None
                ),
                "subsamples_valid": len(sampled),
                "subsample_rho_p10": _round(_quantile(sampled, 0.1)) if sampled else None,
                "subsample_rho_median": _round(_quantile(sampled, 0.5)) if sampled else None,
                "subsample_rho_p90": _round(_quantile(sampled, 0.9)) if sampled else None,
                "subsample_same_sign_fraction": _round(comparison),
            })

    # Redundancy examples across the exact previously highlighted
    # Bliss columns and Essentia head classes (including cross-head pairs).
    spotlight = _correlations(columns, [
        (FOCUS_BLISS[i], FOCUS_BLISS[j])
        for i in range(len(FOCUS_BLISS))
        for j in range(i + 1, len(FOCUS_BLISS))
    ])
    model_keys = [
        f"{head}:{name}"
        for head, names in FOCUS_CLASSES.items()
        for name in names
        if f"{head}:{name}" in columns
    ]
    class_pairs = _correlations(columns, [
        (model_keys[i], model_keys[j])
        for i in range(len(model_keys))
        for j in range(i + 1, len(model_keys))
    ])

    return {
        "schema": REPORT_SCHEMA,
        "status": "POST_SELECTED_WITHIN_COHORT_SENSITIVITY_NOT_EXTERNAL_VALIDATION",
        "songs": n,
        "group_provenance": group,
        "selection": "all_16_pairs_selected_after_inspecting_the_same_100_song_cohort",
        "subsampling": {
            "seed": seed,
            "count": resamples,
            "sample_fraction": sample_fraction,
            "sample_size": sample_size,
            "sampling": "repeated_unstratified_without_replacement_song_subsamples",
            "not_independent_holdout_or_confidence_intervals": True,
        },
        "bliss_redundancy": {
            "all_possible_pairs": len(bliss_pairs),
            "defined_pairs": len(defined),
            "absolute_rho_ge_0_7": sum(
                abs(p["spearman_rho"]) >= .7 for p in defined
            ),
            "absolute_rho_ge_0_9": sum(
                abs(p["spearman_rho"]) >= .9 for p in defined
            ),
            "top_10": defined[:10],
            "focus_pairs": spotlight,
        },
        "essentia_selected_class_redundancy": class_pairs,
        "selected_cross_model_correlations": selected,
        "limitations": {
            "artist_album_recording_groups_not_established": group != "READY",
            "post_selection_same_cohort_winners_curse_possible": True,
            "repeated_song_subsampling_not_an_independent_replication": True,
            "song_nonindependence_from_artist_album_not_corrected": True,
            "no_significance_or_generalization_claim": True,
            "no_teacher_or_metric_fitting": True,
            "no_song_keys_audio_hashes_feature_vectors_exported": True,
            "no_similarity_improvement_claim": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-db", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path,
                        help="New aggregate-only JSON next to the existing private research SQLite")
    parser.add_argument("--resamples", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261030)
    args = parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise FileExistsError("Refusing to overwrite previous aggregate")
        report = analyze(args.research_db, seed=args.seed,
                         resamples=args.resamples)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2,
                      allow_nan=False)
            stream.write("\n")
        print(json.dumps({
            "schema": REPORT_SCHEMA,
            "status": report["status"],
            "songs": report["songs"],
            "group_provenance": report["group_provenance"],
            "bliss_redundancy_defined_pairs": report["bliss_redundancy"]["defined_pairs"],
            "selected_posthoc_pairs_checked": len(report["selected_cross_model_correlations"]),
            "resamples_per_pair": report["subsampling"]["count"],
            "aggregate_created": True,
        }, indent=2))
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error,
            ZeroDivisionError, OverflowError):
        parser.exit(
            2, "WP3 robustness blocked: invalid research snapshot, classes or output; no sources modified\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
