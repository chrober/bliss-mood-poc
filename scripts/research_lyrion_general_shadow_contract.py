#!/usr/bin/env python3
"""Research-only Lyrion General-guidance shadow comparison contract.

An offline, in-memory rehearsal of the EXISTING Bliss-qualified candidate
pool. This is NOT an SPI v2 provider, a production mixer, a General Metric,
a calibrated scoring model, or an LMS plugin. It never selects or mutates
a playlist. Output aggregates contain no candidate IDs, songs or scores.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

SCHEMA = "lyrion-general-shadow-research-request-v1"
RESULT_SCHEMA = "lyrion-general-shadow-research-summary-v1"
MAX_POOL = 50


def shadow_batch(request: dict) -> dict:
    if not isinstance(request, dict) or set(request) != {
        "schema", "mode", "scorer_fingerprint",
        "score_scale_id", "score_orientation",
        "experimental_preview_opt_in", "candidates",
    }:
        raise ValueError("Invalid research-only request contract")
    if request["schema"] != SCHEMA or request["mode"] != "shadow_only":
        raise ValueError("Only shadow-only research requests accepted")
    fp = request["scorer_fingerprint"]
    scale = request["score_scale_id"]
    if not isinstance(fp, str) or not fp or not isinstance(scale, str) or not scale:
        raise ValueError("Model fingerprint and frozen scoring scale required")
    if request["score_orientation"] != "higher_is_more_similar":
        raise ValueError("Score orientation must be explicit")
    optin = request["experimental_preview_opt_in"]
    if type(optin) is not bool:
        raise ValueError("Explicit experimental preview flag must be boolean")
    candidates = request["candidates"]
    if not isinstance(candidates, list) or not (2 <= len(candidates) <= MAX_POOL):
        raise ValueError("Bounded existing Bliss-qualified candidate batch required")
    seen = set()
    source_order = {}
    flags = set()
    for item in candidates:
        if not isinstance(item, dict) or set(item) != {
            "candidate_id", "bliss_rank", "admitted_by_bliss",
            "identity_exact", "feature_present",
            "feature_fingerprint", "essentia_validated",
            "general_score",
        }:
            raise ValueError("Invalid candidate contract")
        key = item["candidate_id"]
        rank = item["bliss_rank"]
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("Candidate identities must be unique and nonempty")
        seen.add(key)
        if type(rank) is not int or rank < 0 or rank >= len(candidates):
            raise ValueError("Invalid baseline rank")
        if rank in source_order:
            raise ValueError("Duplicate existing Bliss rank")
        source_order[rank] = key
        for name in ("admitted_by_bliss", "identity_exact",
                     "feature_present", "essentia_validated"):
            if type(item[name]) is not bool:
                raise ValueError("Candidate evidence flags must be true booleans")
        if not item["admitted_by_bliss"]:
            flags.add("host_admission_violation")
        if not item["identity_exact"]:
            flags.add("exact_track_join_missing")
        if not item["feature_present"]:
            flags.add("missing_feature_row")
        if item["feature_fingerprint"] != fp:
            flags.add("model_fingerprint_mismatch")
        if not item["essentia_validated"] and not optin:
            flags.add("source_parity_unvalidated")
        s = item["general_score"]
        if type(s) not in (float, int) or not math.isfinite(s) or not 0 <= s <= 1:
            flags.add("missing_or_invalid_bounded_general_score")
    if set(source_order) != set(range(len(candidates))):
        raise ValueError("Baseline ranks must cover the complete candidate batch")
    if not optin and any(not x["essentia_validated"] for x in candidates):
        flags.add("source_parity_unvalidated")
    base = [source_order[i] for i in range(len(candidates))]
    stable = {
        "schema": RESULT_SCHEMA,
        "mode": "shadow_only",
        "candidate_pool_size": len(candidates),
        "candidate_pool_admission_unchanged": True,
        "bliss_reference_order_unchanged": True,
        "playlist_queue_or_route_writes": False,
        "provider_spi_implemented": False,
        "general_metric_validated_or_selected": False,
        "personal_metric_activated": False,
        "score_blending_with_existing_bliss_implemented": False,
        "experimental_unvalidated_data_opt_in": optin,
        "shadow_reranking_eligible": len(flags) == 0,
        "neutral_fallback_reasons": sorted(flags),
    }
    if flags:
        return {**stable, "status": "NEUTRAL_SHADOW_NO_COMPARABLE_FULL_BATCH",
                "changed_positions": 0, "top5_overlap": None,
                "max_absolute_rank_shift": None}
    by_key = {item["candidate_id"]: item for item in candidates}
    proposed = sorted(base, key=lambda k: (
        -float(by_key[k]["general_score"]), by_key[k]["bliss_rank"]))
    newrank = {key: i for i, key in enumerate(proposed)}
    changed = sum(newrank[k] != i for i, k in enumerate(base))
    max_shift = max(abs(newrank[k]-i) for i, k in enumerate(base))
    k = min(5, len(base))
    overlap = len(set(base[:k]) & set(proposed[:k]))
    return {
        **stable,
        "status": "SHADOW_REORDERING_SUMMARY_ONLY",
        "changed_positions": changed,
        "top5_overlap": overlap,
        "max_absolute_rank_shift": max_shift,
        "metrics_are_not_musical_quality_or_playback_improvement": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.request.is_file() or args.request.stat().st_size > 200000:
            raise ValueError("Refuse oversized or absent shadow request")
        request = json.loads(args.request.read_text(encoding="utf-8"))
        report = shadow_batch(request)
        print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError,
            json.JSONDecodeError):
        print("Lyrion research shadow contract REJECTED (no playlist changes)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
