#!/usr/bin/env python3
"""WP1-E6: pinned CCMSim source-subset upper bounds, *not* audio clearance.

Public CC BY 4.0 aggregate pair *endpoints* and source identities only; no
human score values, participant response files, original audio, model runs,
audio source HTTP probing, source file paths in report, or private music.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
import sys
from audit_wp1_e4_ccmsim_metadata import (
    profile, read_csv, pinned_download, MAPPING_COLUMNS, LABEL_COLUMNS,
    SOURCES, FILES, COMMIT,
)

SCHEMA = "wp1-e6-ccmsim-source-coverage-and-access-gate-v1"
# Preregister source combinations for *coverage upper bounds*.
# "Open catalog" is NOT a recording copyright or a permitted download.
SUBSETS = {
    "fma_only": ("fma",),
    "mtt_only": ("magnatagatune",),
    "lyra_only": ("lyra",),
    "fma_plus_mtt": ("fma", "magnatagatune"),
    "fma_plus_lyra": ("fma", "lyra"),
    "mtt_plus_lyra": ("magnatagatune", "lyra"),
    "fma_plus_mtt_plus_lyra": ("fma", "magnatagatune", "lyra"),
    "all_nine_source_upper_bound": tuple(SOURCES),
}
ACCESS = {
    "magnatagatune": "publisher_original_archive_access_unreliable_in_prior_7_of_30_test",
    "fma": "public_dataset_audio_index_per_recording_copyright_must_be_reviewed",
    "corpusCOFLA": "source_describes_upon_request",
    "arabandalusian": "source_describes_registration_required",
    "lyra": "source_describes_youtube_id_no_audio_rights_confirmed",
    "makam": "source_describes_registration_required",
    "hindustani": "source_describes_registration_required",
    "carnatic": "source_describes_registration_required",
    "jingju": "source_describes_registration_required",
}
if set(ACCESS) != set(SOURCES):
    raise ValueError("Every source needs explicit access status")


def coverage(mapping_raw: bytes, human_raw: bytes) -> dict:
    # This validates published original annotation values only for source
    # format; the subsequent ranking/coverage never accesses those fields.
    verified = profile(mapping_raw, human_raw)
    mapping = read_csv(mapping_raw, MAPPING_COLUMNS)
    human = read_csv(human_raw, LABEL_COLUMNS)
    sources = {r["survey_audio_id"]: r["dataset"] for r in mapping}
    clips_by_source = defaultdict(set)
    pair_by_relation = Counter()
    pairs = []
    for row in human:
        a, b = row["audio_pair"].split("-")
        source_a, source_b = sources[a], sources[b]
        clips_by_source[source_a].add(a)
        clips_by_source[source_b].add(b)
        n = int(row["num_annotators"])
        if not (1 <= n <= 5):
            raise ValueError("Unexpected annotator count")
        pairs.append((source_a,source_b,n))
        pair_by_relation["|".join(sorted((source_a,source_b)))]+=1

    subset_results = {}
    for title, source_tuple in SUBSETS.items():
        allowed = set(source_tuple)
        cohort=[x for x in pairs if x[0] in allowed and x[1] in allowed]
        if not cohort:
            raise ValueError("Predeclared source subset has no observed labels")
        singles=sum(n==1 for a,b,n in cohort)
        replicated=len(cohort)-singles
        within=sum(a==b for a,b,n in cohort)
        subset_results[title]={
            "sources": list(source_tuple),
            "source_count": len(source_tuple),
            "clip_upper_bound": sum(len(clips_by_source[s]) for s in allowed),
            "pair_upper_bound": len(cohort),
            "pair_fraction_of_1130": round(len(cohort)/1130,6),
            "single_annotator_pairs": singles,
            "replicated_annotator_pairs": replicated,
            "within_source_pairs": within,
            "cross_source_pairs": len(cohort)-within,
            "any_actual_audio_or_model_coverage_verified": False,
            "audio_rights_verified": False,
            "independent_artist_or_recording_groups_verified": False,
        }
    source_results={}
    for source in SOURCES:
        source_results[source]={
            "pinned_mapping_clip_count":sum(
                x["dataset"]==source for x in mapping),
            "annotated_clip_count":len(clips_by_source[source]),
            "within_source_human_pairs":
                pair_by_relation[source+"|"+source],
            "metadata_access_category": ACCESS[source],
            "legal_permission_to_download_redistribute_or_model_audio": "NOT_DETERMINED",
            "clip_identity_and_20s_segment_parity_verified_with_source_audio":False,
        }
    if (len(mapping)!=486 or len(human)!=1130
        or sum(len(clips_by_source[s]) for s in SOURCES)!=463
        or sum(pair_by_relation.values())!=1130):
        raise ValueError("Pin/cohort count drift")
    if not 1 <= len(pair_by_relation) <= 45:
        raise ValueError("Invalid source-pair category inventory")
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_PUBLIC_AGGREGATED_PAIR_SOURCE_COVERAGE_ONLY",
        "upstream_commit":COMMIT,
        "pinned_git_blob_sha1":{
            "clip_mapping":FILES[
                "data/annotations/audio_annotations_mapping.csv"][0],
            "human_pair_aggregate":FILES[
                "data/annotations/human_similarity.csv"][0],
        },
        "source_annotation_license":"CC-BY-4.0",
        "third_party_audio_license_cleared":False,
        "source_corpus_count":9,
        "mapped_audio_clips":486,
        "annotated_audio_clips":463,
        "annotated_human_pairs":1130,
        "single_annotator_pairs":verified[
            "observed_annotator_votes_per_pair"]["1"],
        "source_pair_category_count":len(pair_by_relation),
        "all_source_pair_counts":dict(sorted(pair_by_relation.items())),
        "source_coverage":source_results,
        "fixed_upper_bound_subsets":subset_results,
        "human_similarity_values_used_for_selection":False,
        "private_rater_responses_or_original_audio_used":False,
        "raw_pair_ids_or_track_paths_or_scores_exported":False,
        "source_probe_or_audio_download_performed":False,
        "no_permission_to_fetch_audio_inferred_from_metadata":True,
        "same_recording_model_predictions_measured":False,
        "independent_general_metric_holdout_established":False,
        "general_metric_selected":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():
            raise ValueError("Require new report in an existing directory")
        report=coverage(
            pinned_download("data/annotations/audio_annotations_mapping.csv"),
            pinned_download("data/annotations/human_similarity.csv"),
        )
        with a.out.open("x",encoding="utf-8",newline="\n") as fh:
            json.dump(report,fh,indent=2,sort_keys=True,allow_nan=False)
            fh.write("\n")
        print(json.dumps({
            "status":report["status"],
            "subset_upper_bounds":{
                k:v["pair_upper_bound"]
                for k,v in report["fixed_upper_bound_subsets"].items()
            },
            "actual_audio_or_model_coverage_measured":False
        },sort_keys=True))
        return 0
    except (OSError,ValueError,UnicodeError,KeyError,TypeError) as exc:
        print("WP1-E6 metadata-only source feasibility BLOCKED",file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
