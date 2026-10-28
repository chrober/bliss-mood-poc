#!/usr/bin/env python3
"""Evaluate the private, already-rated 12-pair listening pilot against sealed model scores.

Read-only local inputs: the human-rated listening-pairs.csv and the original
selection-audit-private.json from propose_local_embedding_ab_pilot.py.
No audio, ONNX, feature SQLite, internet, LMS/queue changes, or dependencies.
Outputs are aggregate and numbered-pair-only reports in a NEW ignored directory.
The deliberately model-selected pilot is diagnostic, not a general-metric holdout.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import statistics
import sys

CSV_FIELDS = (
    "left", "right", "genre_similarity_1to5", "mood_energy_similarity_1to5",
    "timbre_similarity_1to5", "next_track_suitability_1to5",
    "confidence_1to3", "notes",
)
RATINGS = CSV_FIELDS[2:6]
SCORES = (
    "genre_cosine", "genre_centered_cosine", "mood_cosine",
    "mood_centered_cosine", "embedding_cosine",
)
EXPECTED_SCHEMA = "private_blinded_local_ab_pilot_selection_v1"
EXPECTED_PAIRS = 12
MIN_N = 3


def _decode_review(raw: bytes) -> tuple[str, str]:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def read_reviews(path: Path) -> tuple[list[dict], dict]:
    """Support UTF-8/Excel CP1252 and comma/semicolon/tab, preserving exact song keys."""
    text, encoding = _decode_review(path.read_bytes())
    lines = text.splitlines()
    if not lines:
        raise ValueError("Review file is empty")
    header = lines[0]
    delimiter = max((",", ";", "\t"), key=header.count)
    if not header.count(delimiter):
        raise ValueError("Review header lacks a supported delimiter")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    if reader.fieldnames is None or list(reader.fieldnames) != list(CSV_FIELDS):
        raise ValueError("Review must have exactly the eight expected columns in original order")
    rows = []
    seen_pairs, seen_tracks = set(), set()
    for number, row in enumerate(reader, 1):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed review CSV row {number} (delimiter or quoting)")
        a, b = row["left"], row["right"]
        if not a or not b or a == b:
            raise ValueError(f"Invalid song identity in review row {number}")
        unordered = frozenset((a, b))
        if unordered in seen_pairs:
            raise ValueError(f"Duplicated unordered pair in review row {number}")
        seen_pairs.add(unordered)
        seen_tracks.update((a, b))
        ratings = {}
        for field in RATINGS + ("confidence_1to3",):
            value = row[field].strip()
            upper = 3 if field == "confidence_1to3" else 5
            if value not in tuple(str(n) for n in range(1, upper + 1)):
                raise ValueError(f"Review row {number}: {field} must be a completed integer 1..{upper}")
            ratings[field] = int(value)
        rows.append({"pair_number": number, "left": a, "right": b,
                     "ratings": ratings, "has_note": bool(row["notes"].strip())})
    if len(rows) != EXPECTED_PAIRS or len(seen_tracks) != 2 * EXPECTED_PAIRS:
        raise ValueError("Expected 12 completed pairs containing exactly 24 distinct songs")
    return rows, {"encoding": encoding,
                  "delimiter": {"\t": "tab", ";": "semicolon", ",": "comma"}[delimiter]}


def read_audit(path: Path, reviews: list[dict]) -> list[dict]:
    """The exact selected order AND left/right orientation must match the reviewed CSV."""
    audit = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(audit, dict) or audit.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("Incorrect sealed selection-audit schema")
    pairs = audit.get("pairs_private_do_not_open_before_review")
    if not isinstance(pairs, list) or len(pairs) != EXPECTED_PAIRS:
        raise ValueError("Sealed audit must contain exactly 12 pairs")
    data = []
    for idx, (review, item) in enumerate(zip(reviews, pairs), 1):
        if (not isinstance(item, dict) or item.get("pair_number") != idx
                or review["left"] != item.get("left")
                or review["right"] != item.get("right")):
            raise ValueError(f"Audit and review identities/order differ at pair {idx}; no scoring")
        raw_scores = item.get("similarity_scores_not_probabilities")
        if not isinstance(raw_scores, dict) or set(raw_scores) != set(SCORES):
            raise ValueError(f"Missing or unexpected similarity score fields for pair {idx}")
        scores = {}
        for name in SCORES:
            value = raw_scores[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Non-numeric {name} for pair {idx}")
            value = float(value)
            if not math.isfinite(value) or not -1.000001 <= value <= 1.000001:
                raise ValueError(f"Invalid similarity score {name} for pair {idx}")
            scores[name] = value
        data.append({"pair_number": idx, "scores": scores,
                     "ratings": review["ratings"],
                     "has_note": review["has_note"],
                     "stratum": item.get("selection_stratum_not_human_label", "unspecified")})
    return data


def average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[pos]]:
            end += 1
        rank = (pos + end - 1) / 2.0
        for k in range(pos, end):
            ranks[ordered[k]] = rank
        pos = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < MIN_N or len(x) != len(y):
        return None
    ax, ay = statistics.mean(x), statistics.mean(y)
    dx, dy = [v - ax for v in x], [v - ay for v in y]
    xx, yy = sum(v*v for v in dx), sum(v*v for v in dy)
    if xx <= 0 or yy <= 0:
        return None
    return sum(a*b for a, b in zip(dx, dy)) / math.sqrt(xx*yy)


def spearman(x: list[float], y: list[float]) -> float | None:
    return pearson(average_ranks(x), average_ranks(y))


def kendall_tau_b(x: list[float], y: list[float]) -> tuple[float | None, dict]:
    if len(x) < MIN_N or len(x) != len(y):
        return None, {}
    concordant = discordant = x_only = y_only = both = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                both += 1
            elif dx == 0:
                x_only += 1
            elif dy == 0:
                y_only += 1
            elif dx == dy:
                concordant += 1
            else:
                discordant += 1
    denominator = (concordant + discordant + x_only) * (
        concordant + discordant + y_only
    )
    tau = (concordant - discordant)/math.sqrt(denominator) if denominator else None
    return tau, {"concordant": concordant, "discordant": discordant,
                 "model_ties_only": x_only, "human_ties_only": y_only,
                 "both_tied": both}


def loo_spearman(x: list[float], y: list[float]) -> list[float]:
    if len(x) < MIN_N + 1:
        return []
    result = []
    for removed in range(len(x)):
        rho = spearman(x[:removed] + x[removed+1:],
                       y[:removed] + y[removed+1:])
        if rho is not None:
            result.append(rho)
    return result


def metric_record(rows: list[dict], model: str, rating: str) -> dict:
    x = [r["scores"][model] for r in rows]
    y = [r["ratings"][rating] for r in rows]
    n = len(x)
    rho = spearman(x, y)
    tau, comparisons = kendall_tau_b(x, y)
    loo = loo_spearman(x, y)
    model_ranks = average_ranks(x)
    human_ranks = average_ranks(y)
    scale = max(1, n-1)
    gaps = []
    for idx, (a, b) in enumerate(zip(model_ranks, human_ranks)):
        difference = (a-b)/scale
        gaps.append({
            "pair_number": rows[idx]["pair_number"],
            "model_minus_human_rank_percentile": round(difference, 6),
            "type": ("model_overpredicts_similarity" if difference > 0
                     else "model_underpredicts_similarity" if difference < 0
                     else "tie"),
        })
    gaps.sort(key=lambda r: (-abs(r["model_minus_human_rank_percentile"]),
                             r["pair_number"]))
    return {
        "n": n,
        "spearman_rho": _rounded(rho),
        "kendall_tau_b": _rounded(tau),
        "pair_ordering": comparisons,
        "loo_spearman_min": _rounded(min(loo)) if loo else None,
        "loo_spearman_max": _rounded(max(loo)) if loo else None,
        "largest_rank_disagreements": gaps[:3],
    }


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def summarize(rows: list[dict]) -> dict:
    if len(rows) < MIN_N:
        raise ValueError("At least three pairs are needed for rank statistics")
    dimensions = {}
    for name in RATINGS:
        values = [r["ratings"][name] for r in rows]
        dimensions[name] = {
            "mean": round(statistics.mean(values), 6),
            "counts_1_to_5": {str(v): values.count(v) for v in range(1, 6)},
            "rated_4_or_5": sum(v >= 4 for v in values),
        }
    correlations = {
        model: {rating: metric_record(rows, model, rating) for rating in RATINGS}
        for model in SCORES
    }
    return {"n": len(rows), "rated_dimensions": dimensions,
            "model_vs_human": correlations}


def _parse_pair_numbers(text: str) -> list[int]:
    if not text.strip():
        return []
    numbers = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece.isdigit() or not 1 <= int(piece) <= EXPECTED_PAIRS:
            raise ValueError("Nonmusic pair numbers must be comma-separated integers 1..12")
        numbers.append(int(piece))
    if len(numbers) != len(set(numbers)):
        raise ValueError("Duplicate nonmusic pair number")
    return sorted(numbers)


def evaluate(review: Path, audit: Path, out_dir: Path, *, nonmusic: str = "") -> dict:
    if out_dir.exists():
        raise FileExistsError("Output directory already exists; never overwrite previous results")
    reviews, review_format = read_reviews(review)
    combined = read_audit(audit, reviews)
    nonmusic_pairs = _parse_pair_numbers(nonmusic)
    music_rows = [row for row in combined if row["pair_number"] not in nonmusic_pairs]
    if len(music_rows) < MIN_N:
        raise ValueError("Too few remaining music pairs after exclusions")
    all_results = summarize(combined)
    music_results = summarize(music_rows)
    details = []
    for row in combined:
        r = {"pair_number": row["pair_number"],
             "nonmusic_flag": row["pair_number"] in nonmusic_pairs,
             "selection_stratum_model_hypothesis": row["stratum"],
             "confidence_1to3": row["ratings"]["confidence_1to3"],
             "has_comment": row["has_note"]}
        r.update({field: row["ratings"][field] for field in RATINGS})
        r.update(row["scores"])
        details.append(r)
    summary = {
        "schema": "local_blinded_listening_pilot12_evaluation_v1",
        "status": "EXPLORATORY_ONLY_NO_GENERAL_METRIC_SELECTED",
        "review_file_format": review_format,
        "pairs_total": EXPECTED_PAIRS,
        "unique_songs": 24,
        "numeric_ratings_valid": EXPECTED_PAIRS * 5,
        "pairs_with_note": sum(item["has_note"] for item in combined),
        "confidence_counts_1_to_3": {
            str(k): sum(item["ratings"]["confidence_1to3"] == k for item in combined)
            for k in (1, 2, 3)
        },
        "nonmusic_pairs_explicitly_flagged": nonmusic_pairs,
        "complete_sample_including_nonmusic": all_results,
        "musical_pairs_sensitivity_excluding_flagged": music_results,
        "methodological_limits": [
            "12 deliberately model-selected pairs, not a random sample or independent holdout",
            "Only one human rater; no general-purpose winner, fitted fusion weights or p-values",
            "Do not optimize a similarity metric on this pilot and reuse it as test evidence",
            "Genre/mood/timbre ratings differ from directed next-track suitability",
            "Model score ranks and human 1..5 ordinal ties require tie-aware statistics",
            "Explicit nonmusic flags indicate data-quality sensitivity, not wrong human ratings",
            "Model ranks are recomputed only within the evaluated 12/remaining selected pairs",
        ],
    }
    # No user identities, music paths, original comments or feature vectors
    # are written, even to the private numbered-pair report.
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "aggregate-model-comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "numbered-pair-details-private.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ratings", type=Path, required=True,
                        help="Human-rated CSV, including Excel tab/semicolon and CP1252 formats")
    parser.add_argument("--selection-audit", type=Path, required=True,
                        help="Sealed original private JSON of model scores and exact pair order")
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="NEW local output directory, never overwrites")
    parser.add_argument("--nonmusic-pairs", default="",
                        help="Explicit 1-based pair numbers, comma-separated; e.g. 10")
    args = parser.parse_args()
    try:
        result = evaluate(args.ratings, args.selection_audit, args.out_dir,
                          nonmusic=args.nonmusic_pairs)
    except (ValueError, UnicodeError, OSError, KeyError, TypeError,
            json.JSONDecodeError) as exc:
        # Do not print raw file paths, recording identities or private JSON.
        parser.exit(2, "Pilot evaluation failed: " + str(exc).splitlines()[0] + "\n")
    print(json.dumps({
        "status": result["status"], "pairs_total": result["pairs_total"],
        "nonmusic_pairs_explicitly_flagged": result["nonmusic_pairs_explicitly_flagged"],
        "music_only_n": result["musical_pairs_sensitivity_excluding_flagged"]["n"],
        "rated_dimensions": result["complete_sample_including_nonmusic"]["rated_dimensions"],
        "model_comparison": {
            model: {dimension: {k: values[k] for k in ("spearman_rho", "kendall_tau_b")}
                    for dimension, values in per_dimension.items()}
            for model, per_dimension in
            result["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"].items()
        },
        "note": "Exploratory pilot only; output contains numbered-pair diagnostics without song identities.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
