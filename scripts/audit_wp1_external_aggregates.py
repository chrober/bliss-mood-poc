#!/usr/bin/env python3
"""WP1-E1: verify and summarize three locked PUBLIC GitHub Actions aggregates.

Reads only archived JSON aggregate members, never audio, track keys, vectors,
ratings or model files. Comparisons stay separate by task and cohort.
Missing global pair-fusion results remain UNMEASURED, never zero or imputed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

SCHEMA = "wp1-e1-external-aggregate-audit-v1"
KEYS = ("mtt", "fma", "deam")
MTT_BASE = ("embedding_cosine", "genre_cosine", "mood_cosine",
            "genre_centered_cosine", "mood_centered_cosine")
MTT_LOCAL = ("rank_audio_genre_equal", "rank_audio_mood_equal",
             "rank_genre_mood_equal", "rank_audio_genre_mood_equal")
FMA_METHODS = MTT_BASE[:]
DEAM_METHODS = ("rms", "cosine", "centered_cosine", "weighted_jaccard",
                "topk_weighted_jaccard", "topk6_ranked_jaccard",
                "topk12_ranked_jaccard")
GLOBAL_METHODS = ("global_genre_mood_equal", "global_genre_audio_equal",
                  "global_mood_audio_equal", "global_genre_mood_audio_equal")


def _finite(value, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Nonfinite or nonnumeric benchmark metric")
    x = float(value)
    if (low is not None and x < low - 1e-12) or (
            high is not None and x > high + 1e-12):
        raise ValueError("Metric outside expected range")
    return x


def _exact(d, key, expected):
    if d.get(key) != expected:
        raise ValueError("Frozen benchmark scope mismatch: " + key)


def _archive_member(path: Path, record: dict) -> dict:
    if not path.is_file() or path.stat().st_size > 10_000_000:
        raise ValueError("Missing/oversized public aggregate ZIP")
    if path.suffix.lower() == ".json":
        if path.name != Path(record["member"]).name or path.stat().st_size > 2_000_000:
            raise ValueError("Expected exact extracted aggregate JSON member")
        raw = path.read_bytes()
    else:
        with zipfile.ZipFile(path) as z:
            member = record["member"]
            entries = z.infolist()
            matching = [i for i in entries if i.filename == member]
            if len(matching) != 1 or matching[0].file_size > 2_000_000:
                raise ValueError("Expected exact unique aggregate JSON member")
            raw = z.read(matching[0])
    if hashlib.sha256(raw).hexdigest() != record["member_sha256"]:
        raise ValueError("Frozen GitHub Actions aggregate SHA256 mismatch")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Aggregate must be a JSON object")
    return data


def _mtt(d: dict, source: dict) -> dict:
    _exact(d, "status", "EXPLORATORY_346_MTT_NO_UNSEEN_HOLDOUT")
    _exact(d, "total_unique_triplets", source["question_count"])
    _exact(d, "human_scorable_triplets", source["decisive_count"])
    _exact(d, "unique_clips", source["unique_clips"])
    _exact(d, "human_ties", 53)
    _exact(d, "paired_same_audio_and_questions", True)
    _exact(d, "representation_comparison",
           "fixed_equal_rank_fusions_with_audio_genre_mood_baselines")
    _exact(d["fixed_rank_fusions"], "triplet_local", True)
    _exact(d["fixed_rank_fusions"], "no_label_fit", True)
    methods = d["methods"]
    if set(methods) != set(MTT_BASE + MTT_LOCAL):
        raise ValueError("Unexpected MTT representation method inventory")
    scores = {}
    for name, row in methods.items():
        n = source["decisive_count"]
        correct, predicted = row["correct"], row["predicted"]
        undefined, ties = row["undefined"], row["metric_ties"]
        if (any(type(v) is not int for v in (correct, predicted, undefined, ties))
                or correct < 0 or predicted < correct
                or predicted + undefined + ties != n):
            raise ValueError("MTT coverage/counts invalid")
        coverage = _finite(row["prediction_coverage"], 0, 1)
        acc = _finite(row["accuracy_with_abstentions_as_incorrect"], 0, 1)
        if (not math.isclose(coverage, predicted / n, abs_tol=1e-12)
                or not math.isclose(acc, correct / n, abs_tol=1e-12)):
            raise ValueError("MTT denominator or coverage drift")
        scores[name] = {"correct": correct, "scorable": n, "predicted": predicted,
                        "metric_ties": ties, "undefined": undefined,
                        "coverage": coverage, "majority_accuracy": acc}
    return {
        "task": source["task"], "status": "COMPLETED_EXPLORATORY_NO_HOLDOUT",
        "questions_total": 346, "decisive_questions": 293, "unique_clips": 1019,
        "same_question_audio_paired": True,
        "methods": scores,
        "best_observed_baseline": "mood_centered_cosine",
        "global_pairwise_fusions_measured": False,
        "triplet_local_rank_fusions_are_not_global_pair_scores": True,
    }


def _fma(d: dict, source: dict) -> dict:
    _exact(d, "schema", "fma-catalog-screened-80-embedding-vs-heads-v1")
    _exact(d, "status", "FMA_VALIDATION_EXPLORATORY_NOT_INDEPENDENT_HOLDOUT")
    _exact(d, "official_split", "validation")
    _exact(d, "sample_size", source["sample_songs"])
    _exact(d, "distinct_artists", source["distinct_artists"])
    _exact(d, "sample_id_sha256", source["sample_id_sha256"])
    methods = d["methods"]
    if set(methods) != set(FMA_METHODS):
        raise ValueError("FMA method coverage or baseline inventory drift")
    scores = {}
    for name, row in methods.items():
        _exact(row, "query_denominator", 80)
        if row["full_queries"] + row["abstained_queries"] != 80:
            raise ValueError("FMA queries do not sum to frozen denominator")
        cv = _finite(row["query_coverage"], 0, 1)
        if not math.isclose(cv, row["full_queries"] / 80, abs_tol=1e-12):
            raise ValueError("FMA query coverage differs")
        scores[name] = {
            "p_at_5": _finite(row["precision_at_5"], 0, 1),
            "map_at_10": _finite(row["map_at_10"], 0, 1),
            "ndcg_at_10": _finite(row["ndcg_at_10"], 0, 1),
            "query_coverage": cv,
        }
    return {
        "task": source["task"], "status": "COMPLETED_EXPLORATORY_VALIDATION_ONLY",
        "official_split": "validation", "untouched_official_test": True,
        "sample_songs": 80, "distinct_artists": 80,
        "queries_same_79_candidates": True, "methods": scores,
        "best_observed_p_at_5": "genre_centered_cosine",
        "global_pairwise_fusions_measured": False,
        "known_teacher_pretraining_overlap_absent": False,
    }


def _deam(d: dict, source: dict) -> dict:
    _exact(d, "schema", "deam-similarity-benchmark-v1")
    cohort = d["dataset"]
    _exact(cohort, "songs_evaluated", source["sample_songs"])
    _exact(cohort, "sample_id_sha256", source["sample_id_sha256"])
    if cohort["annotation_cohort_counts"] != {
            "earlier_excerpt": 197, "full_song_2015": 43}:
        raise ValueError("DEAM collection strata or sample drift")
    mood = d["per_head"]["moodtheme"]
    if set(mood) != set(DEAM_METHODS):
        raise ValueError("DEAM 56D baseline method inventory differs")
    scores = {}
    for name, row in mood.items():
        axis = row["axes"]["valence_arousal"]
        count = axis["query_count"]
        if type(count) is not int or not 0 <= count <= 240:
            raise ValueError("DEAM query count invalid")
        scores[name] = {
            "valence_arousal_mean_query_spearman":
                _finite(axis["mean_query_spearman"], -1, 1),
            "valid_queries": count,
            "query_coverage": count / 240,
        }
    if scores["cosine"]["valid_queries"] != 240:
        raise ValueError("DEAM frozen baseline lost full query coverage")
    return {
        "task": source["task"], "status": "COMPLETED_EXPLORATORY_BASELINE",
        "sample_songs": 240, "collection_strata": {"earlier_excerpt": 197,
                                                  "full_song_2015": 43},
        "methods": scores,
        "best_observed_mood_va_rho": "weighted_jaccard",
        "embedded1280_paired_results_measured": False,
        "global_pairwise_fusions_measured": False,
        "teacher_pretraining_overlap_ruled_out": False,
    }


def audit(lock: dict, paths: dict[str, Path]) -> dict:
    _exact(lock, "schema", "wp1-e1-external-aggregate-lock-v1")
    if set(paths) != set(KEYS) or set(lock["artifacts"]) != set(KEYS):
        raise ValueError("Exactly three immutable benchmark inputs are required")
    artifacts = lock["artifacts"]
    data = {key: _archive_member(paths[key], artifacts[key]) for key in KEYS}
    r = {
        "schema": SCHEMA,
        "status": "VERIFIED_HISTORICAL_PUBLIC_AGGREGATES_NO_NEW_AUDIO_OR_FUSION",
        "evidence": {
            "mtt": _mtt(data["mtt"], artifacts["mtt"]),
            "fma": _fma(data["fma"], artifacts["fma"]),
            "deam": _deam(data["deam"], artifacts["deam"]),
        },
        "sources": {name: {"run_id": artifacts[name]["run_id"],
                            "artifact_id": artifacts[name]["artifact_id"],
                            "member_sha256": artifacts[name]["member_sha256"]}
                    for name in KEYS},
        "feature_coverage": {
            "mtt": {"genre87": True, "moodtheme56": True,
                    "embedding1280": True, "bliss23": "NOT_VERIFIED"},
            "fma": {"genre87": True, "moodtheme56": True,
                    "embedding1280": True, "bliss23": "NOT_VERIFIED"},
            "deam": {"genre87": True, "moodtheme56": True,
                     "embedding1280": "NOT_VERIFIED_ON_SAME_COHORT",
                     "bliss23": "NOT_VERIFIED"},
        },
        "remaining_gaps": lock["unmeasured"],
        "cross_task_score_averaged": False,
        "unmeasured_global_fusions_imputed": False,
        "human_perceptual_winner_selected": False,
        "official_fma_test_touched": False,
        "personal_metric_selected": False,
    }
    if tuple(r["remaining_gaps"]["mtt_global_pairwise_equal_weight_fusions"]
             ["method_ids"]) != GLOBAL_METHODS:
        raise ValueError("Global pairwise predeclared method list drift")
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mtt-zip", required=True, type=Path)
    p.add_argument("--fma-zip", required=True, type=Path)
    p.add_argument("--deam-zip", required=True, type=Path)
    p.add_argument("--lock", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    try:
        if a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():
            raise ValueError("Write only to a fresh destination")
        lock = json.loads(a.lock.read_text(encoding="utf-8"))
        result = audit(lock, {"mtt": a.mtt_zip, "fma": a.fma_zip,
                              "deam": a.deam_zip})
        with a.out.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, allow_nan=False)
            f.write("\n")
        print(json.dumps({"schema": SCHEMA, "status": result["status"],
                          "archived_public_aggregates_verified": 3,
                          "global_fusions_measured": False,
                          "output": str(a.out)}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            json.JSONDecodeError) as e:
        print("WP1-E1 aggregate verification BLOCKED: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
