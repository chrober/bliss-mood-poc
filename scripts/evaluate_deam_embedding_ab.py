#!/usr/bin/env python3
"""Strict paired 240-song DEAM A/B: 1280D raw embedding vs Mood/Genre heads.

All features are produced on the SAME catalog-screened annotated DEAM clips.
Only aggregate mean per-query Spearman and paired sensitivity leave the runner.
DEAM Valence/Arousal is an emotion proximity proxy, not playlist quality,
and is not proven disjoint from the model's full original training set.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

import benchmark_deam as deam
import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import filename_for_key, validate_embedding
from mtt_paired_evidence import quantile

SAMPLE_SHA = "db12c5d2692285638a4c25af442f29fd75391eb86cd7f1ea88d2f565d12630d0"
ANNOTATION_SHA = "809b0feb4ba6196c1eda9b2b7b33b892b11fa71457cfceb0d47e832ed1a5f15f"
AUDIO_SHA = "e2814325f573ade8caebc697f0efcfdf7207142b737d72558a416117ca591353"
METADATA_SHA = "3d1d5ab42e852803a770f2cfbd685c6b464e1ebe76f26b0e10954597902b90f8"
MTG_SHA = "bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca"
PREPROCESSING = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
# Frozen before new embeddings, from successful filtered DEAM run 39579552118.
MOOD_COSINE_REFERENCE = {
    "valence": 0.16424605171402107,
    "arousal": 0.2726358463243648,
    "valence_arousal": 0.286784551387186,
}
AXES = ("valence", "arousal", "valence_arousal")
METHODS = {
    "embedding_cosine": ("embedding", ev.cosine),
    "mood_cosine": ("moodtheme", ev.cosine),
    "mood_centered_cosine": ("moodtheme", ev.centered_cosine),
    "genre_cosine": ("genre", ev.cosine),
    "genre_centered_cosine": ("genre", ev.centered_cosine),
}
GROUPS = ("earlier_excerpt", "full_song_2015")


def sample_hash(ids: list[str]) -> str:
    return hashlib.sha256(("\n".join(ids) + "\n").encode("ascii")).hexdigest()


def validate_selected(ids: list[str], annotations: dict, expected: str) -> None:
    if len(ids) != 240 or len(set(ids)) != 240 or sample_hash(ids) != expected:
        raise ValueError("DEAM frozen 240-song filtered sample fingerprint changed")
    if not set(ids) <= set(annotations):
        raise ValueError("Missing song-level DEAM human VA annotation")
    counts = {c: sum(deam.annotation_cohort(i) == c for i in ids) for c in GROUPS}
    if counts != {"earlier_excerpt": 197, "full_song_2015": 43}:
        raise ValueError("DEAM two collection cohort sizes changed")


def read_representations(db: Path, embedding_dir: Path,
                         ids: list[str]) -> tuple[dict, str, str]:
    keys = {i: f"DEAM/{i}.mp3" for i in ids}
    expected = {filename_for_key(k) for k in keys.values()}
    if not embedding_dir.is_dir() or {p.name for p in embedding_dir.iterdir()} != expected:
        raise ValueError("DEAM private 1280D sidecars incomplete or unexpected")
    with closing(ev.open_database(db)) as conn:
        cohorts = {head: ev._catalog(conn,head,experimental=True)
                   for head in ("genre","moodtheme")}
        if any(m["preprocessing_version"] != PREPROCESSING for m in cohorts.values()):
            raise ValueError("DEAM requires pinned corrected Rust-v5 cohort")
        data = ev.fetch_keys(conn,set(keys.values()),cohorts)
        out = {}
        fp = encoder_sha = None
        for ident in ids:
            key = keys[ident]
            heads = data[key]
            if set(heads) != set(cohorts):
                raise ValueError("DEAM paired classifier coverage incomplete")
            rows = conn.execute(
                """SELECT f.model_id, f.audio_sha256, f.patches_analyzed,
                          m.embedding_model, m.models_sha256_json
                   FROM feature_tracks f JOIN feature_models m ON f.model_key=m.model_key
                   WHERE f.track_file=? ORDER BY f.model_id""",(key,)
            ).fetchall()
            if len(rows) != 2 or {r[0] for r in rows} != set(cohorts):
                raise ValueError("DEAM two-head provenance missing")
            hashes = {r[1] for r in rows}
            patches = {r[2] for r in rows}
            enc_names = {r[3] for r in rows}
            model_shas = {json.loads(r[4]).get(r[3]) for r in rows}
            if (len(hashes)!=1 or len(patches)!=1 or len(enc_names)!=1
                    or len(model_shas)!=1 or not next(iter(model_shas))):
                raise ValueError("DEAM mixed audio, patches or model heads")
            enc_sha = next(iter(model_shas))
            if encoder_sha is not None and enc_sha != encoder_sha:
                raise ValueError("DEAM mixed ONNX encoders")
            encoder_sha = enc_sha
            with (embedding_dir / filename_for_key(key)).open(encoding="utf8") as f:
                blob = json.load(f)
            vector = validate_embedding(blob,key,next(iter(hashes)),
                                        next(iter(patches)),enc_sha,PREPROCESSING,fp)
            fp = blob["representation_fingerprint"]
            out[ident] = {**heads,"embedding":vector}
    return out,encoder_sha,fp


def paired_va(vectors: dict, ids: list[str], labels: dict,
              *, seed: int, replicates: int = 800) -> dict:
    """Compare all 5 representations on 100% shared candidates/queries.

    If any candidate has an undefined similarity or reference ranks are
    undefined for a method, the whole query abstains and contributes zero
    to ALL axes on a COMMON fixed denominator. Report coverage separately.
    """
    if not 100 <= replicates <= 5000:
        raise ValueError("Resampling replicates out of bounds")
    if len(ids) < 6 or len(set(ids)) != len(ids) or set(vectors) != set(ids):
        raise ValueError("Expected complete distinct DEAM paired song universe")
    groups = defaultdict(list)
    for ix,song in enumerate(ids):
        groups[deam.annotation_cohort(song)].append(ix)
    if not groups or not set(groups).issubset(set(GROUPS)):
        raise ValueError("DEAM paired resampling requires known annotation protocols")
    results = {name:{axis:[] for axis in AXES} for name in METHODS}
    diagnostics={name:{"queries_complete":0,"queries_abstained":0,
                       "candidate_scores_undefined":0} for name in METHODS}
    for anchor in ids:
        rest = [x for x in ids if x != anchor]
        human = {}
        for axis in AXES:
            ix = AXES.index(axis)
            def difference(b):
                dv=abs(labels[anchor][0]-labels[b][0])
                da=abs(labels[anchor][1]-labels[b][1])
                return -((dv,da,math.hypot(dv,da))[ix])
            human[axis]=[difference(x) for x in rest]
        for name,(rep,fn) in METHODS.items():
            sims=[]
            for other in rest:
                score=fn(vectors[anchor][rep],vectors[other][rep])
                if score is None or not math.isfinite(score):
                    diagnostics[name]["candidate_scores_undefined"] += 1
                    continue
                sims.append(score)
            values={axis:deam.spearman(sims,human[axis]) for axis in AXES} if len(sims)==len(rest) else {}
            if len(values) != 3 or any(v is None or not math.isfinite(v) for v in values.values()):
                diagnostics[name]["queries_abstained"] += 1
                for axis in AXES:
                    results[name][axis].append(0.)
            else:
                diagnostics[name]["queries_complete"] += 1
                for axis in AXES:
                    results[name][axis].append(values[axis])
    rng=random.Random(seed)
    # All comparisons use same resampling draws, preserving 197/43 protocol ratio.
    samples=[[rng.choice(items) for _,items in sorted(groups.items()) for _ in items]
             for _ in range(replicates)]
    metrics={}
    for name,per_axis in results.items():
        metrics[name]={
            **diagnostics[name],
            "query_denominator":len(ids),
            "query_coverage":diagnostics[name]["queries_complete"]/len(ids),
            "axes":{axis:statistics.fmean(per_axis[axis]) for axis in AXES},
        }
    compared={}
    for baseline in (m for m in METHODS if m!="embedding_cosine"):
        compared[baseline]={}
        for axis in AXES:
            deltas=[a-b for a,b in zip(results["embedding_cosine"][axis],
                                       results[baseline][axis])]
            draws=sorted(statistics.fmean(deltas[i] for i in sample)
                         for sample in samples)
            compared[baseline][axis]={
                "embedding_minus_baseline":statistics.fmean(deltas),
                "shared_stratified_query_95pct_sensitivity":
                    [quantile(draws,.025),quantile(draws,.975)],
                "paired_queries":len(ids),
            }
    return {
        "methods":metrics,"paired_differences":compared,
        "common_candidate_count_per_query":len(ids)-1,
        "policy":{
            "all_methods_same_song_keys_queries_candidates":True,
            "undefined_similarity_whole_query_abstention_zero":True,
            "fixed_query_denominator":len(ids),
            "stratified_resampling_replicates":replicates,
            "stratified_resampling_seed":seed,
            "strata_counts":{k:len(v) for k,v in sorted(groups.items())},
            "interval_status":"descriptive_query_sensitivity_NOT_independent_CI",
        },
    }


def evaluate(db: Path, embeddings: Path, ids: list[str],
             annotations: dict, prior: dict) -> dict:
    validate_selected(ids,annotations,SAMPLE_SHA)
    if (prior["dataset"]["sample_id_sha256"]!=SAMPLE_SHA
            or prior["dataset"]["train_overlap_check"] !=
            "partial_catalog_exact_artist_title_exclusion_NOT_verified_training_disjointness"):
        raise ValueError("Prior DEAM screened 240-run is not the registered baseline")
    vectors,encoder_sha,fp=read_representations(db,embeddings,ids)
    result=paired_va(vectors,ids,annotations,seed=20261021)
    for axis in AXES:
        value=result["methods"]["mood_cosine"]["axes"][axis]
        previous=prior["per_head"]["moodtheme"]["cosine"]["axes"][axis]["mean_query_spearman"]
        if abs(value-previous)>1e-9 or abs(value-MOOD_COSINE_REFERENCE[axis])>1e-9:
            raise ValueError("Paired DEAM mood cosine baseline changed from original 240 run")
    subcohorts={}
    for group in GROUPS:
        included=[id for id in ids if deam.annotation_cohort(id)==group]
        subcohorts[group]={
            "songs":len(included),
            "evaluation":paired_va(
                {k:vectors[k] for k in included},included,annotations,seed=20261021,
                replicates=400,
            ),
        }
        prior_group=prior["subcohorts"][group]["per_head"]["moodtheme"]["cosine"]["axes"]
        for axis in AXES:
            score=subcohorts[group]["evaluation"]["methods"]["mood_cosine"]["axes"][axis]
            if abs(score-prior_group[axis]["mean_query_spearman"])>1e-9:
                raise ValueError("DEAM same-protocol subcohort mood cosine baseline changed")
    return {
        "schema":"deam-240-screened-embedding-vs-heads-paired-v1",
        "status":"DEAM_CATALOG_FILTERED_EXPLORATORY_NOT_PROVEN_TRAIN_INDEPENDENT",
        "dataset":"DEAM",
        "songs":240,
        "sample_id_sha256":SAMPLE_SHA,
        "annotation_cohorts":{"earlier_excerpt":197,"full_song_2015":43},
        "human_reference":"averaged_song_valence_arousal_1_to_9",
        "embedding_encoder_sha256":encoder_sha,
        "embedding_representation_fingerprint":fp,
        "reference_baseline_exactly_reproduced":True,
        "full_cohort":result,
        "within_protocol_subcohorts":subcohorts,
        "limitations":[
            "VA distance is a labeled emotion-proximity proxy, not rated pairwise song similarity or transition quality.",
            "DEAM 2013/2014 excerpt and 2015 full-song annotations follow heterogeneous protocols.",
            "Older and 2015 samples intentionally not prevalence weighted.",
            "Cross-query resampling intervals are descriptive because candidates are shared.",
            "MTG artist/title screen only excluded possible exact catalog matches, not proved encoder/heads training-disjoint.",
            "This is the previously explored filtered 240-song development sample, NOT independent unseen test.",
            "No production choice or fusion-parameter optimization from this cohort.",
            "Only aggregate statistical fields, never DEAM song IDs, human labels per song, artists, audio or embedding vectors.",
        ],
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations-zip",type=Path,required=True)
    p.add_argument("--audio-zip",type=Path,required=True)
    p.add_argument("--deam-metadata-zip",type=Path,required=True)
    p.add_argument("--mtg-metadata-tsv",type=Path,required=True)
    p.add_argument("--db",type=Path,required=True)
    p.add_argument("--embedding-dir",type=Path,required=True)
    p.add_argument("--previous-filtered-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():
        p.error("Never overwrite a paired DEAM A/B report")
    for name,path,expected in (
        ("DEAM human annotations",args.annotations_zip,ANNOTATION_SHA),
        ("DEAM audio",args.audio_zip,AUDIO_SHA),
        ("DEAM metadata",args.deam_metadata_zip,METADATA_SHA),
        ("MTG catalog",args.mtg_metadata_tsv,MTG_SHA),
    ):
        if deam.sha256_file(path)!=expected:
            raise ValueError("Registered DEAM source SHA differs: "+name)
    previous=json.loads(args.previous_filtered_report.read_text(encoding="utf8"))
    if (previous["dataset"]["annotation_archive_sha256"]!=ANNOTATION_SHA
            or previous["dataset"]["audio_archive_sha256"]!=AUDIO_SHA
            or previous["dataset"]["overlap_screen"]["deam_metadata_sha256"]!=METADATA_SHA
            or previous["dataset"]["overlap_screen"]["mtg_raw_metadata_sha256"]!=MTG_SHA):
        raise ValueError("Prior filtered DEAM report has different publisher provenance")
    labels=deam.load_annotations(args.annotations_zip)
    members=deam.match_audio(args.audio_zip,labels)
    screened,audit=deam.screen_catalog_overlaps(
        members,labels,args.deam_metadata_zip,args.mtg_metadata_tsv)
    if (audit["excluded_mtg_catalog_candidates"]!=75
            or audit["eligible_after_exclusion"]!=1727):
        raise ValueError("DEAM catalog screening cohort changed")
    ids=deam.select_ids(labels,screened,240,20261021,stratify_cohorts=True)
    validate_selected(ids,labels,SAMPLE_SHA)
    output=evaluate(args.db,args.embedding_dir,ids,labels,previous)
    output["source_sha256"]={
        "audio_zip":AUDIO_SHA,"annotations_zip":ANNOTATION_SHA,
        "metadata_zip":METADATA_SHA,"mtg_catalog":MTG_SHA,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf8") as f:
        json.dump(output,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps({
        "status":output["status"],"songs":output["songs"],
        "baseline_exact":output["reference_baseline_exactly_reproduced"],
        "methods":output["full_cohort"]["methods"],
        "cohorts":{k:v["songs"] for k,v in output["within_protocol_subcohorts"].items()},
    },indent=2))


if __name__=="__main__":
    main()
