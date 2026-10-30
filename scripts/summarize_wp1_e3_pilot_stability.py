#!/usr/bin/env python3
"""WP1-E3: read ONLY the existing anonymous 12-pair aggregate for stability.

Never reads original ratings, private selection audit, song IDs, private
numbered-pair diagnostics, features, source DB or audio. Output is a compact
privacy-preserving 12-versus-11 plus music-11 LOO Spearman report.
This diagnostic is post-hoc, not inference on an independent holdout.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

SCHEMA = "wp1-e3-local12-aggregate-stability-only-v1"
SOURCE_SCHEMA = "local_blinded_listening_pilot12_evaluation_v1"
MODELS = (
    "genre_cosine", "genre_centered_cosine",
    "mood_cosine", "mood_centered_cosine", "embedding_cosine",
)
RATINGS = (
    "genre_similarity_1to5", "mood_energy_similarity_1to5",
    "timbre_similarity_1to5", "next_track_suitability_1to5",
)


def _coefficient(obj, key):
    value=obj.get(key)
    if value is None:
        return None
    if type(value) not in (float,int) or not math.isfinite(value) or not -1<=value<=1:
        raise ValueError("Invalid aggregate rank-correlation statistic")
    return float(value)


def summarize(source: dict) -> dict:
    if (not isinstance(source,dict)
            or source.get("schema") != SOURCE_SCHEMA
            or source.get("status") != "EXPLORATORY_ONLY_NO_GENERAL_METRIC_SELECTED"
            or type(source.get("pairs_total")) is not int
            or source["pairs_total"] != 12
            or source.get("nonmusic_pairs_explicitly_flagged") != [10]):
        raise ValueError("Expected the exact existing original 12-pair anonymous report")
    full=source.get("complete_sample_including_nonmusic")
    music=source.get("musical_pairs_sensitivity_excluding_flagged")
    if not isinstance(full,dict) or not isinstance(music,dict):
        raise ValueError("Both frozen samples are necessary")
    if (type(full.get("n")) is not int or full["n"] != 12
            or type(music.get("n")) is not int or music["n"] != 11):
        raise ValueError("Wrong original pilot sample size")
    if (set(full.get("model_vs_human",{})) != set(MODELS)
            or set(music.get("model_vs_human",{})) != set(MODELS)):
        raise ValueError("Missing/extra model score channels")
    output={}
    for model in MODELS:
        if (set(full["model_vs_human"][model]) != set(RATINGS)
                or set(music["model_vs_human"][model]) != set(RATINGS)):
            raise ValueError("Missing/extra human rating channels")
        item={}
        for target in RATINGS:
            all_row=full["model_vs_human"][model][target]
            music_row=music["model_vs_human"][model][target]
            if (all_row.get("n") != 12 or music_row.get("n") != 11):
                raise ValueError("Mismatched metric denominator")
            rho12=_coefficient(all_row,"spearman_rho")
            rho11=_coefficient(music_row,"spearman_rho")
            loo_min=_coefficient(music_row,"loo_spearman_min")
            loo_max=_coefficient(music_row,"loo_spearman_max")
            if None in (rho12,rho11,loo_min,loo_max) or loo_min>loo_max:
                raise ValueError("Insufficient finite Spearman/LOO data")
            item[target]={
                "rho_12_including_nonmusic":round(rho12,6),
                "rho_11_music_only":round(rho11,6),
                "rho_change_excluding_pair10":round(rho11-rho12,6),
                "music_11_leave_one_out_rho_min":round(loo_min,6),
                "music_11_leave_one_out_rho_max":round(loo_max,6),
                "music_11_loo_contains_negative_and_positive":
                    loo_min < 0 < loo_max,
                "metric_winner_claimed":False,
            }
        output[model]=item
    return {
        "schema":SCHEMA,
        "status":"EXPLORATORY_SENSITIVITY_NO_INDEPENDENT_VALIDATION",
        "original_human_pairs":12,"music_only_pairs":11,
        "preserved_original_nonmusic_pair_number":10,
        "sample_selected_using_models":True,
        "human_raters":1,
        "model_score_channels":len(MODELS),
        "human_rating_dimensions":len(RATINGS),
        "comparison_cells":len(MODELS)*len(RATINGS),
        "source_full_aggregate_only":True,
        "original_ratings_or_audit_or_song_ids_used":False,
        "ranks_not_optimized_or_blended":True,
        "confidence_interval_or_significance_computed":False,
        "general_metric_selected":False,
        "results":output,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate",required=True,type=Path)
    args=parser.parse_args()
    try:
        # Refuse huge file or sidecar. Path is never printed on failure.
        if not args.aggregate.is_file() or args.aggregate.stat().st_size > 1_000_000:
            raise ValueError("Aggregate unavailable or unexpectedly large")
        raw=json.loads(args.aggregate.read_text(encoding="utf-8"))
        report=summarize(raw)
    except (OSError,UnicodeError,ValueError,TypeError,KeyError,
            json.JSONDecodeError):
        print("WP1-E3 aggregate-only sensitivity blocked: source contract invalid",
              file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False,
                     allow_nan=False))
    return 0


if __name__=="__main__":
    sys.exit(main())
