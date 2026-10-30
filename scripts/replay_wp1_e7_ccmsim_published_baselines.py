#!/usr/bin/env python3
"""WP1-E7: independently replay authors' already-published pair-score baselines.

No audio or new model inference. Exact upstream CCMSim public combined scores
and human aggregate are SHA-pinned. Spearman is recomputed from published
rows, stratified into all/within-source/cross-source; no learned fusion,
unpaired significance, private labels or song/participant identifiers out.
These are published models, NOT any Lyrion/Bliss/Essentia scorer.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict
import io
import json
import math
from pathlib import Path
import sys
import urllib.request
from audit_wp1_e4_ccmsim_metadata import (
    COMMIT, ORIGIN, MAPPING_COLUMNS, LABEL_COLUMNS,
    pinned_download, profile, read_csv, git_blob_sha,
)
SCHEMA="wp1-e7-ccmsim-published-11-method-baselines-v1"
COMBINED="data/combined_similarities.csv"
COMBINED_GIT_SHA="b0d475c6f58f5d0ec2fbdeaaca57d87f472a2c3d"
HUMAN=("H-Overall","H-Cultural","H-Recommend")
MODEL=(
    "SP-Melody","SP-Rhythm","SP-Harmony","SP-Timbre",
    "FM-MERT_95","FM-MERT_330","FM-CULTURE_MERT",
    "FM-CULTURE_MERT_TA","FM-CLAP_MUSIC",
    "FM-CLAP_MUSIC_SPEECH","FM-QWEN",
)
SAMPLES=("all_published_pairs","within_source_only","cross_source_only")

def download_combined(opener=urllib.request.urlopen):
    req=urllib.request.Request(ORIGIN+COMBINED,headers={
        "User-Agent":"bliss-mood-poc-wp1-e7-published-baselines/1.0",
        "Accept-Encoding":"identity"})
    with opener(req,timeout=30) as response:
        if (response.status!=200 or response.geturl()!=ORIGIN+COMBINED
            or response.headers.get("Content-Encoding","identity").lower()!="identity"):
            raise ValueError("Unexpected upstream baseline source response")
        b=response.read(300001)
    if len(b)>300000 or git_blob_sha(b)!=COMBINED_GIT_SHA:
        raise ValueError("Original model baseline blob drift")
    return b

def ranks(values):
    """Average ranks for exact ties, no scipy/network dependency."""
    n=len(values)
    order=sorted(range(n),key=lambda i:values[i])
    rank=[0.0]*n
    pos=0
    while pos<n:
        end=pos+1
        while end<n and values[order[end]]==values[order[pos]]:
            end+=1
        midpoint=(pos+1+end)/2.0
        for j in range(pos,end):
            rank[order[j]]=midpoint
        pos=end
    return rank

def spearman(x,y):
    if len(x)!=len(y) or len(x)<3:
        raise ValueError("Insufficient paired observations")
    a=ranks(x);b=ranks(y)
    ax=sum(a)/len(a);by=sum(b)/len(b)
    va=math.fsum((z-ax)**2 for z in a)
    vb=math.fsum((z-by)**2 for z in b)
    if va==0 or vb==0:
        return None
    return math.fsum((p-ax)*(q-by) for p,q in zip(a,b))/math.sqrt(va*vb)

def replay(mapping_raw,human_raw,combined_raw):
    upstream=profile(mapping_raw,human_raw)
    mapping=read_csv(mapping_raw,MAPPING_COLUMNS)
    annotations=read_csv(human_raw,LABEL_COLUMNS)
    models=read_csv(combined_raw,("audio_pair",)+HUMAN+MODEL)
    if len(models)!=1130:
        raise ValueError("Unexpected upstream pair count")
    source_by_clip={r["survey_audio_id"]:r["dataset"] for r in mapping}
    labels={r["audio_pair"]:r for r in annotations}
    if len(labels)!=1130:
        raise ValueError("Duplicate original pair labels")
    data=defaultdict(list)
    observed=Counter()
    visited=set()
    for row in models:
        key=row["audio_pair"]
        if key in visited or key not in labels:
            raise ValueError("Unknown or duplicated original model pair")
        visited.add(key)
        original=labels[key]
        a,b=key.split("-")
        if a not in source_by_clip or b not in source_by_clip:
            raise ValueError("Unmapped original clip")
        stratum="within_source_only" if source_by_clip[a]==source_by_clip[b] else "cross_source_only"
        observed[stratum]+=1
        for src,dest in zip(HUMAN,(
            "overall_music_similarity","cultural_similarity","recommendation_level")):
            v=float(row[src]);human=float(original[dest])
            if not (math.isfinite(v) and -1e-12<=v<=1+1e-12 and
                    math.isclose(v,human,rel_tol=0,abs_tol=1e-12)):
                raise ValueError("Combined file did not preserve original human score")
        for name in MODEL:
            v=float(row[name])
            if not math.isfinite(v) or not 0<=v<=1:
                raise ValueError("Invalid original published model score")
        data["all_published_pairs"].append(row)
        data[stratum].append(row)
    if (len(visited)!=1130 or observed["within_source_only"]!=112
        or observed["cross_source_only"]!=1018):
        raise ValueError("Original human-model source coverage changed")
    metrics={}
    for cohort in SAMPLES:
        rows=data[cohort]
        metrics[cohort]={
            "pair_count":len(rows),
            "human_label_targets":{
                target:{
                    name:(
                        round(score,8) if score is not None else None
                    ) for name in MODEL for score in [spearman(
                        [float(x[name]) for x in rows],
                        [float(x[target]) for x in rows]
                    )]
                }
                for target in HUMAN
            },
            "true_independent_song_group_effective_n_known":False,
        }
    return {
        "schema":SCHEMA,
        "status":"REPLAYED_PUBLISHED_THIRD_PARTY_MODEL_PAIR_SCORES_NO_NEW_INFERENCE",
        "upstream_commit":COMMIT,
        "source_combined_git_blob_sha1":COMBINED_GIT_SHA,
        "published_original_human_pair_count":upstream["published_unique_annotated_pairs"],
        "model_count":len(MODEL),
        "human_target_count":len(HUMAN),
        "source_strata":metrics,
        "score_metric":"tie_aware_spearman_rank_correlation_on_published_pair_rows",
        "model_families_are_third_party_not_essentia_bliss_or_lyrion":True,
        "original_published_study_results_replayed_not_independent_test":True,
        "human_votes_seen_during_prior_software_development":True,
        "song_group_bootstrap_confidence_intervals_computed":False,
        "musical_metric_winner_selected":False,
        "global_pairwise_lyrion_general_metric_tested":False,
        "source_audio_or_participant_responses_fetched":False,
        "original_pair_ids_features_and_raw_scores_exported":False,
        "third_party_audio_rights_verified":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
            raise ValueError("Output must be new file")
        result=replay(
            pinned_download("data/annotations/audio_annotations_mapping.csv"),
            pinned_download("data/annotations/human_similarity.csv"),
            download_combined())
        with args.out.open("x",encoding="utf-8",newline="\n") as fp:
            json.dump(result,fp,indent=2,sort_keys=True,allow_nan=False)
            fp.write("\n")
        print(json.dumps({
            "schema":result["schema"],
            "status":result["status"],
            "published_model_families":result["model_count"],
            "actual_lyrion_general_metric_tested":False},sort_keys=True))
        return 0
    except (OSError,UnicodeError,ValueError,KeyError,TypeError,csv.Error):
        print("WP1-E7 published model baseline replay BLOCKED",file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
