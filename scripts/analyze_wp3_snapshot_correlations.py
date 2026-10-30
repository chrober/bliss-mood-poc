#!/usr/bin/env python3
"""Descriptive Bliss23 ↔ Essentia Genre87/MoodTheme56 correlations.

Read ONLY an existing private WP3 SQLite. No LMS identities, audio scanning,
ONNX, model fitting, holdout, classifier ground truth, or claims of improved
musical similarity. Python 3.15 stdlib only. Never export tracks or vectors.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import statistics
import struct
import sys

from audit_bliss_essentia_join import BLISS_COLUMNS

SCHEMA = "lyrion-wp3-research-snapshot-v1"
REPORT_SCHEMA = "wp3-bliss-essentia-descriptive-correlations-v1"
HEAD_DIMS = {"genre": 87, "moodtheme": 56}
MIN_TRACKS = 3


def _pearson(a: tuple[float, ...], b: tuple[float, ...]) -> float | None:
    if len(a) != len(b) or len(a) < MIN_TRACKS:
        raise ValueError("Correlation arrays must have the same eligible population")
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    xa = [x - ma for x in a]
    xb = [x - mb for x in b]
    sa = sum(x * x for x in xa)
    sb = sum(x * x for x in xb)
    if sa <= 1e-24 or sb <= 1e-24:
        return None
    value = sum(x * y for x, y in zip(xa, xb)) / math.sqrt(sa * sb)
    return max(-1.0, min(1.0, value))


def _midranks(values: tuple[float, ...]) -> tuple[float, ...]:
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranked = [0.0] * len(values)
    cursor = 0
    while cursor < len(values):
        end = cursor + 1
        while end < len(values) and values[indexed[end]] == values[indexed[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for index in indexed[cursor:end]:
            ranked[index] = rank
        cursor = end
    return tuple(ranked)


def _vector(blob: object, size: int, kind: str) -> tuple[float, ...]:
    fmt = {"d": "d", "f": "f"}[kind]
    if not isinstance(blob, bytes) or len(blob) != size * struct.calcsize(fmt):
        raise ValueError("Unexpected private research vector size")
    vals = struct.unpack("<" + fmt * size, blob)
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("Nonfinite private research features")
    return vals


def _read(db: Path) -> tuple[list[tuple[float, ...]], dict[str, list[tuple[float, ...]]], dict, str]:
    if not db.is_file():
        raise ValueError("Private research SQLite is missing")
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        con.execute("PRAGMA query_only=ON")
        if con.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Unrecognized WP3 research SQLite version")
        meta = dict(con.execute("SELECT key, value FROM metadata"))
        if meta.get("schema") != SCHEMA:
            raise ValueError("Unrecognized WP3 research SQLite schema")
        selection = json.loads(meta["selection_json"])
        labels = {}
        for head, width in HEAD_DIMS.items():
            items = selection["chosen_head_model_ids"][head]["class_labels"]
            if (not isinstance(items, list) or len(items) != width
                    or len(set(items)) != width
                    or any(not isinstance(x, str) or not x for x in items)):
                raise ValueError("Invalid classifier label catalog")
            labels[head] = items
        seen = set()
        bliss, heads = [], {head: [] for head in HEAD_DIMS}
        for key, x, g, m in con.execute("""
            SELECT track_key, bliss_f64_le, genre_f32_le, moodtheme_f32_le
              FROM paired_tracks ORDER BY track_key COLLATE BINARY
        """):
            if not isinstance(key, str) or not key or key in seen:
                raise ValueError("Invalid research track key")
            seen.add(key)
            bliss.append(_vector(x, 23, "d"))
            heads["genre"].append(_vector(g, 87, "f"))
            heads["moodtheme"].append(_vector(m, 56, "f"))
        if not MIN_TRACKS <= len(bliss) <= 300:
            raise ValueError("Descriptive research cohort must contain 3..300 songs")
        return bliss, heads, labels, meta.get("group_readiness", "UNKNOWN")


def describe(db: Path, *, top: int = 8) -> dict:
    if type(top) is not int or not 1 <= top <= 30:
        raise ValueError("Descriptive top-K must be between 1 and 30")
    bliss, heads, labels, group_status = _read(db)
    xcols = [tuple(row[i] for row in bliss) for i in range(len(BLISS_COLUMNS))]
    xranks = [_midranks(values) for values in xcols]
    result = {}
    for head, width in HEAD_DIMS.items():
        ycols = [tuple(row[j] for row in heads[head]) for j in range(width)]
        yranks = [_midranks(values) for values in ycols]
        correlations = []
        undefined = 0
        for i, xv in enumerate(xcols):
            for j, yv in enumerate(ycols):
                pearson = _pearson(xv, yv)
                spearman = _pearson(xranks[i], yranks[j])
                if pearson is None or spearman is None:
                    undefined += 1
                    continue
                correlations.append({
                    "bliss_feature": BLISS_COLUMNS[i],
                    "essentia_head": head,
                    "essentia_class": labels[head][j],
                    "pearson_r": round(pearson, 6),
                    "spearman_rho": round(spearman, 6),
                })
        # Sorting uses the unrounded estimates only to select feature pairs;
        # ties between distinct original pairs are deterministically ordered.
        correlations.sort(key=lambda item: (
            -abs(item["spearman_rho"]), item["bliss_feature"],
            item["essentia_class"],
        ))
        magnitudes = [abs(x["spearman_rho"]) for x in correlations]
        result[head] = {
            "total_pairs": len(BLISS_COLUMNS) * width,
            "defined_pairs": len(correlations),
            "undefined_constant_or_degenerate_pairs": undefined,
            "median_abs_spearman": round(statistics.median(magnitudes), 6)
                                    if magnitudes else None,
            "pairs_abs_spearman_ge_0_3": sum(x >= 0.3 for x in magnitudes),
            "pairs_abs_spearman_ge_0_5": sum(x >= 0.5 for x in magnitudes),
            "pairs_abs_spearman_ge_0_7": sum(x >= 0.7 for x in magnitudes),
            "top_absolute_spearman_pairs_exploratory": correlations[:top],
        }
    return {
        "schema": REPORT_SCHEMA,
        "status": "DESCRIPTIVE_COHORT_ONLY_NOT_GROUP_HELDOUT_VALIDATION",
        "songs": len(bliss),
        "bliss_dimensions": len(BLISS_COLUMNS),
        "essentia_dimensions": HEAD_DIMS,
        "group_provenance": group_status,
        "estimators": {
            "pearson": "ordinary sample correlation on source feature values",
            "spearman": "Pearson correlation of tie-aware midranks",
        },
        "heads": result,
        "limitations": {
            "no_group_disjoint_inference_or_significance_claims": True,
            "multiple_comparisons_no_confirmatory_pvalues": True,
            "same_native_100_songs_selection_bias_possible": True,
            "pearson_and_spearman_not_independent_quality_metrics": True,
            "no_raw_track_identifiers_or_feature_vectors_exported": True,
            "correlation_is_not_musical_similarity_improvement": True,
            "no_metric_learning_or_model_fitting_performed": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--research-db", type=Path, required=True)
    p.add_argument("--out", type=Path,
                   help="New private aggregate report (refuses overwrite); otherwise stdout")
    p.add_argument("--top", type=int, default=8)
    args = p.parse_args()
    try:
        if args.out is not None and (args.out.exists() or args.out.is_symlink()):
            raise FileExistsError("Aggregate report already exists")
        obj = describe(args.research_db, top=args.top)
        payload = json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.out is None:
            print(payload, end="")
        else:
            with args.out.open("x", encoding="utf-8") as file:
                file.write(payload)
            print(json.dumps({
                "schema": REPORT_SCHEMA,
                "status": obj["status"],
                "songs": obj["songs"],
                "group_provenance": obj["group_provenance"],
                "genre_defined_pairs": obj["heads"]["genre"]["defined_pairs"],
                "moodtheme_defined_pairs": obj["heads"]["moodtheme"]["defined_pairs"],
                "aggregate_created": True,
            }, indent=2))
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error,
            OverflowError, ZeroDivisionError):
        p.exit(2, "Descriptive research analysis failed safely: check local private WP3 DB schema and data; no input modified\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
