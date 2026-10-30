#!/usr/bin/env python3
"""WP1-E5: label-blind CCMSim song-disjoint holdout feasibility (metadata only).

Uses the exact E4 SHA-locked, CC BY 4.0 *aggregated* CSVs only. Accesses
public pair IDs, source dataset and annotation COUNT for grouping; not human
rating values, original audio, participant responses, recording paths in
output, model features, private music or production scores.

No model fitting, independent musical-quality test, or metric selection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

from audit_wp1_e4_ccmsim_metadata import (
    LABEL_COLUMNS, MAPPING_COLUMNS, SOURCES, COMMIT, FILES,
    pinned_download, profile, read_csv,
)

SCHEMA = "wp1-e5-ccmsim-source-stratified-clip-disjoint-feasibility-v1"
SEEDS = (3, 4, 7, 13, 21)  # upstream paper's declared test seeds; no seed search
POLICIES = ("train60_validation20_test20", "five_disjoint_clip_folds")


def _ranked(ids: set[str], dataset: str, seed: int) -> list[str]:
    # One deterministic hashing order per dataset; do not examine human scores
    return sorted(ids, key=lambda value: (
        hashlib.sha256(
            f"WP1-E5-track-only-v1|{seed}|{dataset}|{value}".encode("utf-8")
        ).digest(), value
    ))


def _balanced_counts(n: int, slots: int) -> list[int]:
    return [n // slots + (i < n % slots) for i in range(slots)]


def _assign(active_by_source: dict[str, set[str]], seed: int, policy: str):
    if policy not in POLICIES or seed not in SEEDS:
        raise ValueError("Unregistered split policy or seed")
    assigned = {}
    folds = (
        ("train", "validation", "test")
        if policy == "train60_validation20_test20"
        else ("fold0", "fold1", "fold2", "fold3", "fold4")
    )
    source_track_counts = {}
    for dataset in SOURCES:
        ids = _ranked(active_by_source.get(dataset, set()), dataset, seed)
        n = len(ids)
        if policy == "train60_validation20_test20":
            # Largest-remainder approximately 60/20/20, deterministic.
            desired = [n * 3 / 5, n / 5, n / 5]
            sizes = [int(x) for x in desired]
            order = sorted(range(3),
                           key=lambda i: (-(desired[i] - sizes[i]), i))
            for i in order[:n - sum(sizes)]:
                sizes[i] += 1
        else:
            sizes = _balanced_counts(n, 5)
        pos = 0
        source_track_counts[dataset] = {}
        for name, amount in zip(folds, sizes):
            for clip in ids[pos:pos+amount]:
                if clip in assigned:
                    raise ValueError("Repeated source identity across assignments")
                assigned[clip] = name
            pos += amount
            source_track_counts[dataset][name] = amount
        if pos != n:
            raise AssertionError("Source assignment cardinality drift")
    return assigned, source_track_counts, folds


def partition_profile(mapping_rows: list[dict], label_rows: list[dict],
                      *, seed: int, policy: str) -> dict:
    # Only survey ID, source dataset, pair membership, annotator count are
    # consulted; NEVER numeric human overall/culture/recommendation scores.
    source_by_id = {}
    for row in mapping_rows:
        key, source = row["survey_audio_id"], row["dataset"]
        if key in source_by_id or source not in SOURCES:
            raise ValueError("Mapping identity invalid")
        source_by_id[key] = source
    active_by_source = defaultdict(set)
    pairs = []
    for row in label_rows:
        pair = row["audio_pair"].split("-")
        if len(pair) != 2 or pair[0] == pair[1] or any(
            x not in source_by_id for x in pair
        ):
            raise ValueError("Invalid public pair source references")
        for key in pair:
            active_by_source[source_by_id[key]].add(key)
        votes = row["num_annotators"]
        if not votes.isdecimal() or not 1 <= int(votes) <= 5:
            raise ValueError("Bad annotator-count support")
        pairs.append((pair[0], pair[1], int(votes)))
    if len(pairs) != 1130 or sum(map(len, active_by_source.values())) != 463:
        raise ValueError("Unknown CCMSim cohort; refuse split")
    assigned, source_track_counts, slots = _assign(
        active_by_source, seed, policy)
    if len(assigned) != 463:
        raise AssertionError("Clip assignment coverage drift")
    retained = Counter()
    source_type = defaultdict(Counter)
    annotation = defaultdict(Counter)
    cross_partition = 0
    retained_source_pairs = defaultdict(Counter)
    for a, b, annotators in pairs:
        group_a, group_b = assigned[a], assigned[b]
        if group_a != group_b:
            cross_partition += 1
            continue
        retained[group_a] += 1
        annotation[group_a][str(annotators)] += 1
        da, db = source_by_id[a], source_by_id[b]
        source_type[group_a]["within_dataset" if da == db
                             else "cross_dataset"] += 1
        retained_source_pairs[group_a]["|".join(sorted((da,db)))] += 1

    if sum(retained.values()) + cross_partition != 1130:
        raise AssertionError("Dropped/retained accounting mismatch")
    clip_counts = Counter(assigned.values())
    if sum(clip_counts.values()) != 463:
        raise AssertionError("Track assignments overlap")
    return {
        "seed": seed,
        "policy": policy,
        "clip_counts_by_partition": {
            name: clip_counts[name] for name in slots
        },
        "retained_question_counts_by_partition": {
            name: retained[name] for name in slots
        },
        "retained_pair_type_counts_by_partition": {
            name: {k: source_type[name][k]
                   for k in ("within_dataset", "cross_dataset")}
            for name in slots
        },
        "retained_single_annotator_pair_counts_by_partition": {
            name: annotation[name]["1"] for name in slots
        },
        "retained_source_pair_categories_by_partition": {
            name: len(retained_source_pairs[name]) for name in slots
        },
        "per_source_clip_counts_by_partition": source_track_counts,
        "cross_partition_pairs_quarantined": cross_partition,
        "retained_pairs_total": sum(retained.values()),
        "retained_pair_fraction": round(
            sum(retained.values()) / len(pairs), 6),
        "all_annotated_clip_ids_appear_in_exactly_one_partition": True,
        "all_retained_question_edges_are_clip_disjoint_between_partitions": True,
        "original_artist_album_recording_disjointness_verified": False,
        "speaker_or_music_tradition_independence_verified": False,
        "human_scores_used_for_partition": False,
        "model_score_calculated": False,
        "independent_quality_holdout_certified": False,
    }


def build_report(mapping_raw: bytes, label_raw: bytes) -> dict:
    audited = profile(mapping_raw, label_raw)  # full E4 upstream contracts
    mapping = read_csv(mapping_raw, MAPPING_COLUMNS)
    labels = read_csv(label_raw, LABEL_COLUMNS)
    analyses = [
        partition_profile(mapping, labels, seed=seed, policy=policy)
        for policy in POLICIES for seed in SEEDS
    ]
    # Strict metadata-only stop/go: a test with too few available questions
    # cannot support robust model selection even before annotation noise.
    primary = analyses[0]  # fixed policy train/dev/test and frozen seed 3
    holdout = primary["retained_question_counts_by_partition"]["test"]
    return {
        "schema": SCHEMA,
        "status": "PINNED_PUBLIC_CLIP_SPLIT_FEASIBILITY_NO_MODEL_EVALUATION",
        "source": "pxaris/CCMSim",
        "upstream_commit": COMMIT,
        "pinned_blobs": {
            "human_aggregate": FILES[
                "data/annotations/human_similarity.csv"][0],
            "clip_mapping": FILES[
                "data/annotations/audio_annotations_mapping.csv"][0],
        },
        "published_unique_pairs": audited["published_unique_annotated_pairs"],
        "annotated_distinct_clips": audited[
            "published_unique_audio_clips_used_by_rated_pairs"],
        "source_datasets": len(SOURCES),
        "fixed_seeds": list(SEEDS),
        "predeclared_policies": list(POLICIES),
        "primary_policy": POLICIES[0],
        "primary_seed": SEEDS[0],
        "primary_test_retained_question_count": holdout,
        "primary_test_meets_100_question_minimum": holdout >= 100,
        "primary_test_independence_certified": False,
        "results": analyses,
        "source_clip_ids_or_pair_ids_or_human_labels_exported": False,
        "third_party_audio_requested": False,
        "artist_album_independence_verified": False,
        "same_recording_essentia_or_bliss_features_computed": False,
        "any_model_fitted_or_selected": False,
        "fma_official_test_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
            raise ValueError("Report must not overwrite any existing file")
        result = build_report(
            pinned_download("data/annotations/audio_annotations_mapping.csv"),
            pinned_download("data/annotations/human_similarity.csv"))
        with args.out.open("x", encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, sort_keys=True, indent=2, allow_nan=False)
            fh.write("\n")
        print(json.dumps({
            "schema": result["schema"],
            "status": result["status"],
            "primary_test_question_count":
                result["primary_test_retained_question_count"],
            "primary_test_meets_100_question_minimum":
                result["primary_test_meets_100_question_minimum"],
            "no_model_or_audio": True,
        }, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as err:
        print("WP1-E5 metadata-only independent clip partition BLOCKED",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
