#!/usr/bin/env python3
"""WP1-E3: SHARP paired-discordance bounds from verified public aggregates.

No per-question predictions exist in the historical aggregate files. This
computes *all mathematically feasible* 2x2 correctness tables, not an
inferred matched result, a confidence interval, an observed p value or
independent evidence of musical quality. Input bytes/identities are
verified by the existing WP1-E1 SHA256-locked auditor.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import zipfile

from audit_wp1_external_aggregates import audit

SCHEMA = "wp1-e3-sharp-matched-correctness-bounds-v1"
REFERENCE = "mood_centered_cosine"


def exact_mcnemar_p(a_only: int, b_only: int) -> float:
    """Two-sided exact binomial conditional p, for a *hypothetical* table."""
    if any(type(x) is not int or x < 0 for x in (a_only, b_only)):
        raise ValueError("Invalid hypothetical discordance counts")
    d = a_only + b_only
    if d == 0:
        return 1.0
    tail = sum(math.comb(d, k) for k in range(min(a_only, b_only) + 1))
    return min(1.0, (2 * tail) / (2**d))


def sharp_tables(n: int, a_correct: int, b_correct: int):
    """Enumerate every feasible pairing for two marginals on SAME n rows."""
    if (any(type(v) is not int for v in (n, a_correct, b_correct))
            or n < 1 or not 0 <= a_correct <= n
            or not 0 <= b_correct <= n):
        raise ValueError("Common denominator or correct counts invalid")
    lo, hi = max(0, a_correct + b_correct - n), min(a_correct, b_correct)
    for both in range(lo, hi + 1):
        a_only = a_correct - both
        b_only = b_correct - both
        neither = n - a_correct - b_correct + both
        if min(a_only, b_only, neither) < 0:
            raise AssertionError("Mathematically infeasible pairing")
        yield both, a_only, b_only, neither


def comparison(n: int, a_correct: int, b_correct: int) -> dict:
    # Retain ALL possible joint tables; never choose or hallucinate one.
    tables = list(sharp_tables(n, a_correct, b_correct))
    if not tables:
        raise AssertionError("No feasible correctness pairing")
    disagreement = [a_only + b_only for _, a_only, b_only, _ in tables]
    both_correct = [both for both, _, _, _ in tables]
    possible_p = [exact_mcnemar_p(a_only, b_only)
                  for _, a_only, b_only, _ in tables]
    paired_delta = a_correct - b_correct
    return {
        "reference_correct": a_correct,
        "candidate_correct": b_correct,
        "common_question_denominator": n,
        "reference_minus_candidate_correct": paired_delta,
        "reference_minus_candidate_accuracy_percentage_points":
            round(100.0 * paired_delta/n, 6),
        "sharp_feasible_both_correct_min": min(both_correct),
        "sharp_feasible_both_correct_max": max(both_correct),
        "sharp_feasible_discordant_questions_min": min(disagreement),
        "sharp_feasible_discordant_questions_max": max(disagreement),
        "hypothetical_two_sided_exact_mcnemar_p_min": min(possible_p),
        "hypothetical_two_sided_exact_mcnemar_p_max": max(possible_p),
        "hypothetical_joint_tables": len(tables),
        "actual_joint_correctness_unavailable": True,
        "actual_p_value_estimable": False,
        "paired_confidence_interval_estimable": False,
    }


def report_from_verified_e1(e1: dict) -> dict:
    if (e1.get("schema") != "wp1-e1-external-aggregate-audit-v1"
            or e1.get("status") !=
            "VERIFIED_HISTORICAL_PUBLIC_AGGREGATES_NO_NEW_AUDIO_OR_FUSION"):
        raise ValueError("Require verified WP1-E1 evidence, not copied scores")
    evidence = e1.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"mtt","fma","deam"}:
        raise ValueError("Missing WP1-E1 cohort evidence")
    mtt = evidence["mtt"]
    if (mtt.get("decisive_questions") != 293
            or mtt.get("questions_total") != 346
            or not mtt.get("same_question_audio_paired")
            or mtt.get("global_pairwise_fusions_measured") is not False):
        raise ValueError("MTT cohort/coverage changed; no matched inference")
    methods = mtt["methods"]
    if set(methods) != {
        "embedding_cosine", "genre_cosine", "mood_cosine",
        "genre_centered_cosine", "mood_centered_cosine",
        "rank_audio_genre_equal", "rank_audio_mood_equal",
        "rank_genre_mood_equal", "rank_audio_genre_mood_equal"
    }:
        raise ValueError("Unexpected historical method inventory")
    n = mtt["decisive_questions"]
    reference = methods[REFERENCE]
    if reference["predicted"] != n or reference["correct"] != 193:
        raise ValueError("Historical MTT leading reference drift")
    contrasts = {}
    for name in sorted(set(methods) - {REFERENCE}):
        candidate = methods[name]
        if (candidate["scorable"] != n
                or not 0 <= candidate["correct"] <= n):
            raise ValueError("Missing/invalid common MTT denominator")
        if (candidate["predicted"] + candidate["metric_ties"]
                + candidate["undefined"] != n):
            raise ValueError("MTT coverage and abstention counts drift")
        contrasts[name] = comparison(n, reference["correct"], candidate["correct"])
        contrasts[name]["candidate_nonprediction_as_incorrect"] = (
            candidate["metric_ties"] + candidate["undefined"])
        contrasts[name]["reference_nonprediction_as_incorrect"] = (
            reference["metric_ties"] + reference["undefined"])
        contrasts[name]["method_is_triplet_local_not_global"] = name.startswith("rank_")
    fma = evidence["fma"]
    deam = evidence["deam"]
    if (fma.get("sample_songs") != 80 or
            fma.get("official_split") != "validation" or
            not fma.get("untouched_official_test") or
            deam.get("sample_songs") != 240):
        raise ValueError("External task cohort provenance missing")
    return {
        "schema": SCHEMA,
        "status": "SHARP_MARGINAL_BOUNDS_ONLY_NO_OBSERVED_PAIRED_TEST",
        "historical_reference": REFERENCE,
        "mtt_human_questions_decisive": n,
        "mtt_questions_total": 346,
        "contrasts": contrasts,
        "other_tasks": {
            "fma": {
                "task": "coarse_genre_retrieval_validation",
                "n_queries": 80,
                "official_test_untouched": True,
                "query_level_paired_inference_identifiable": False,
            },
            "deam": {
                "task": "valence_arousal_proximity",
                "n_queries": 240,
                "query_level_paired_inference_identifiable": False,
            },
        },
        "source_sha256_locks": {
            name: e1["sources"][name]["member_sha256"]
            for name in ("mtt", "fma", "deam")
        },
        "all_question_level_joint_correctness_values_missing": True,
        "no_observed_mcnemar_test_or_paired_bootstrap_claimed": True,
        "hypothetical_p_ranges_are_not_confidence_intervals": True,
        "no_multiplicity_adjusted_p_value_or_metric_winner": True,
        "human_mtt_corpus_already_exploratory_not_independent_holdout": True,
        "unmeasured_global_pairwise_fusions_not_imputed": True,
        "private_12_pair_human_ratings_not_read": True,
        "no_audio_or_models_or_per_song_features_used": True,
        "general_metric_selected": False,
    }


def evaluate(lock: dict, paths: dict[str, Path]) -> dict:
    # The E1 auditor verifies historical artifact bytes and ALL cohort
    # contracts, including FMA/DEAM. Never trust a user-authored E1 JSON
    # as proof of verified source provenance.
    return report_from_verified_e1(audit(lock, paths))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("mtt", "fma", "deam"):
        parser.add_argument("--"+arg+"-zip", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
            raise ValueError("Output must be a new file in an existing directory")
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        report = evaluate(lock, {"mtt":args.mtt_zip,"fma":args.fma_zip,
                                 "deam":args.deam_zip})
        with args.out.open("x",encoding="utf-8",newline="\n") as f:
            json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        print(json.dumps({
            "schema":report["schema"],"status":report["status"],
            "matched_contrasts_bounded":len(report["contrasts"]),
            "true_paired_p_values_observed":0,
            "general_metric_selected":False
        },sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,
            json.JSONDecodeError) as exc:
        print("WP1-E3 strict marginal-bounds audit BLOCKED: "+str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
