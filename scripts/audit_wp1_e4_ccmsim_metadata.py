#!/usr/bin/env python3
"""WP1-E4: pinned CCMSim external human-label metadata feasibility only.

Downloads two small, public, CC BY 4.0 published *aggregated annotation*
CSV files (not participant responses, raw audio, sound paths as artifacts,
model vectors or local user data). Validate immutable upstream Git blob
hashes and publish ONLY dataset-level counts and prospective limitations.
This is NOT a model benchmark or quality win.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request

SCHEMA = "wp1-e4-ccmsim-pinned-human-annotations-preflight-v1"
COMMIT = "eff8ab428dd12f1973548d657928b5211dd290bb"
ORIGIN = "https://raw.githubusercontent.com/pxaris/CCMSim/" + COMMIT + "/"
FILES = {
    "data/annotations/audio_annotations_mapping.csv": (
        "0921898a7920858db0472ed11bc222578f80d834", 100_000
    ),
    "data/annotations/human_similarity.csv": (
        "dd1f026ca72cc1616a7a7cdebd333d869d6c6720", 150_000
    ),
}
MAPPING_COLUMNS = (
    "survey_audio_id", "dataset", "audio_file_path",
    "survey_start_second", "survey_end_second",
)
LABEL_COLUMNS = (
    "audio_pair", "overall_music_similarity", "cultural_similarity",
    "recommendation_level", "overall_music_similarity_annotations",
    "cultural_similarity_annotations", "recommendation_level_annotations",
    "num_annotators",
)
SOURCES = (
    "magnatagatune", "fma", "corpusCOFLA",
    "arabandalusian", "lyra", "makam",
    "hindustani", "carnatic", "jingju",
)
LABELS = ("overall_music_similarity","cultural_similarity","recommendation_level")


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def pinned_download(path: str, opener=urllib.request.urlopen) -> bytes:
    if path not in FILES:
        raise ValueError("Only two approved aggregated CSV paths may be fetched")
    expected, limit = FILES[path]
    req = urllib.request.Request(
        ORIGIN + path, headers={
            "User-Agent": "bliss-mood-poc-wp1-e4-metadata-preflight/1.0",
            "Accept-Encoding": "identity",
        })
    with opener(req, timeout=30) as response:
        if response.status != 200 or response.geturl() != ORIGIN + path:
            raise ValueError("Upstream published metadata source changed")
        if response.headers.get("Content-Encoding","identity").lower() != "identity":
            raise ValueError("Compressed upstream response disallowed")
        raw = response.read(limit+1)
    if len(raw) > limit:
        raise ValueError("Metadata size cap exceeded")
    if git_blob_sha(raw) != expected:
        raise ValueError("Immutable upstream Git blob hash differs")
    return raw


def read_csv(raw: bytes, expected: tuple[str, ...]) -> list[dict]:
    text=raw.decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(text,newline=""), strict=True)
    if tuple(reader.fieldnames or ()) != expected:
        raise ValueError("Public annotation table schema mismatch")
    rows=list(reader)
    if any(set(row) != set(expected) or any(value is None for value in row.values())
           for row in rows):
        raise ValueError("Malformed public aggregate row")
    return rows


def profile(mapping_raw: bytes, human_raw: bytes) -> dict:
    mappings=read_csv(mapping_raw,MAPPING_COLUMNS)
    labels=read_csv(human_raw,LABEL_COLUMNS)
    if len(mappings)!=486 or len(labels)!=1130:
        raise ValueError("Frozen upstream cohort counts differ")
    ids={}
    counts=Counter()
    for row in mappings:
        key=row["survey_audio_id"]
        ds=row["dataset"]
        if not key or key in ids or ds not in SOURCES:
            raise ValueError("Missing, duplicate or unknown upstream source ID")
        ids[key]=ds
        counts[ds]+=1
        # Validate segments, but never output source filename or clip path.
        try:
            start,end=float(row["survey_start_second"]),float(row["survey_end_second"])
        except (TypeError,ValueError):
            raise ValueError("Invalid source segment boundaries") from None
        if not 0<=start<end:
            raise ValueError("Invalid source segment duration")
    if any(counts[ds] != 54 for ds in SOURCES):
        raise ValueError("Exact published source mapping has drifted")
    unique_pairs=set()
    referenced=set()
    annot=Counter()
    pair_types=Counter()
    source_edges=Counter()
    label_min={key:float("inf") for key in LABELS}
    label_max={key:float("-inf") for key in LABELS}
    adjacency=defaultdict(set)
    for row in labels:
        pair=row["audio_pair"].split("-")
        if len(pair)!=2 or pair[0]==pair[1] or any(x not in ids for x in pair):
            raise ValueError("Unmapped, malformed or self-similarity pair")
        pair_key=tuple(sorted(pair))
        if pair_key in unique_pairs:
            raise ValueError("Duplicated unordered original human pair")
        unique_pairs.add(pair_key)
        referenced.update(pair_key)
        adjacency[pair[0]].add(pair[1])
        adjacency[pair[1]].add(pair[0])
        ds_a,ds_b=ids[pair[0]],ids[pair[1]]
        pair_types["within_dataset" if ds_a==ds_b else "cross_dataset"]+=1
        source_edges["|".join(sorted((ds_a,ds_b)))]+=1
        count=row["num_annotators"]
        if not count.isdecimal() or int(count) < 1:
            raise ValueError("Invalid original annotator count")
        votes=int(count)
        annot[votes]+=1
        for key in LABELS:
            try:
                val=float(row[key])
            except (TypeError,ValueError):
                raise ValueError("Invalid human similarity aggregate value") from None
            if not 0<=val<=1:
                raise ValueError("Aggregated human similarity outside [0,1]")
            label_min[key]=min(label_min[key],val)
            label_max[key]=max(label_max[key],val)
        # Published per-person lists are left UNREAD; participant identity
        # and the annotator's raw ratings are unnecessary for this audit.
    if len(unique_pairs)!=1130 or len(referenced)!=463:
        raise ValueError("Public unique-pair or annotated-clip cohort differs")
    if sum(k*v for k,v in annot.items())!=1250:
        raise ValueError("Published 125x10 annotation count differs")
    if pair_types["within_dataset"] + pair_types["cross_dataset"]!=1130:
        raise AssertionError("Missing source-classification counts")
    remaining=set(referenced)
    component_sizes=[]
    while remaining:
        root=remaining.pop()
        stack=[root]
        count=0
        while stack:
            node=stack.pop()
            count+=1
            neighbours=adjacency[node]&remaining
            remaining.difference_update(neighbours)
            stack.extend(neighbours)
        component_sizes.append(count)
    return {
        "schema":SCHEMA,
        "status":"REAL_PUBLIC_HUMAN_LABELS_VERIFIED_METADATA_ONLY_NO_AUDIO_OR_FEATURES",
        "external_source":"pxaris/CCMSim",
        "source_commit":COMMIT,
        "pinned_git_blob_sha1":{
            "clip_mapping":FILES["data/annotations/audio_annotations_mapping.csv"][0],
            "human_aggregated_pairs":FILES["data/annotations/human_similarity.csv"][0],
        },
        "annotation_license":"CC-BY-4.0",
        "audio_license":"THIRD_PARTY_PER_SOURCE_UNVERIFIED_FOR_THIS_RESEARCH",
        "publication_documented_participants":125,
        "published_unique_annotated_pairs":len(unique_pairs),
        "published_unique_audio_clips_used_by_rated_pairs":len(referenced),
        "published_mapping_rows":len(mappings),
        "per_dataset_mapping_rows":{ds:counts[ds] for ds in SOURCES},
        "upstream_readme_claims_52_clips_per_dataset_not_same_as_mapping_54":True,
        "mapping_rows_minus_upstream_readme_declared_468":len(mappings)-468,
        "observed_annotator_votes_per_pair":{str(k):annot[k] for k in sorted(annot)},
        "single_annotator_pair_fraction":round(annot[1]/1130,6),
        "all_annotator_votes":sum(k*v for k,v in annot.items()),
        "pair_source_relation":dict(pair_types),
        "pair_source_fraction_cross_dataset":round(pair_types["cross_dataset"]/1130,6),
        "per_label_aggregated_score_min_max":{
            key:{"min":label_min[key],"max":label_max[key]} for key in LABELS
        },
        "pair_graph_source_connected_component_count":len(component_sizes),
        "pair_graph_largest_source_component_size":max(component_sizes),
        "source_clip_to_artist_or_album_grouping_verified":False,
        "same_recording_essentia_predictions_available":False,
        "same_recording_bliss23_features_available":False,
        "independent_from_essentia_training_corpus_verified":False,
        "human_rater_ids_or_raw_votes_or_clip_paths_in_output":False,
        "cross_dataset_cultural_bias_ruled_out":False,
        "general_metric_quality_measured":False,
        "general_metric_selected":False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
            raise ValueError("New report file required")
        report=profile(
            pinned_download("data/annotations/audio_annotations_mapping.csv"),
            pinned_download("data/annotations/human_similarity.csv"))
        with args.out.open("x",encoding="utf-8",newline="\n") as f:
            json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        print(json.dumps({
            "status":report["status"],
            "published_pairs":report["published_unique_annotated_pairs"],
            "single_annotator_pair_fraction":report["single_annotator_pair_fraction"],
            "raw_audio_downloaded":False,
            "general_metric_selected":False,
        },sort_keys=True))
        return 0
    except (OSError,UnicodeError,ValueError,TypeError,KeyError,
            csv.Error,TimeoutError) as error:
        # Deliberately no URLs, raw paths, CSV records or participant data.
        print("WP1-E4 pinned CCMSim metadata feasibility BLOCKED (source/check mismatch)",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    sys.exit(main())
