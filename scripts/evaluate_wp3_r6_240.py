#!/usr/bin/env python3
"""Frozen WP3-R6 teacher-proxy research on 240 NEW native Essentia songs.

Fits scalers, MoodTheme Ridge and Genre PLS on the original 100 only.
Uses NEW 240 Essentia teacher outputs solely for frozen evaluation.
No raw song keys, model weights, audio paths or predictions in stdout.
This is NOT listener-rated musical similarity or metric selection.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys

from research_bliss_essentia_teacher_models import _requires_sklearn
from research_feature_relationships import spearman
from audit_bliss_essentia_join import open_bliss, bliss_vector
from wp3_r6_native_240 import _private_json, SCHEMA as PLAN_SCHEMA
from prepare_wp3_blinded_bliss_student_pilot import _old_grouped_rows, _load_new_bliss

PROTOCOL="wp3-r6-frozen-external-teacher-proxy-protocol-v1"
N=240
DIMS={"genre":87,"moodtheme":56,"voice":2}


def _native_rows(path: Path, keys: list[str], plan: dict) -> dict:
    result={}
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA user_version").fetchone()[0]!=3:
            raise ValueError("Native 240 schema invalid")
        rows=db.execute("""
          SELECT track_file,model_id,audio_sha256,scores_f32_le
          FROM feature_tracks ORDER BY track_file COLLATE BINARY,model_id
        """)
        for key,head,audio,blob in rows:
            if (key not in plan["private_source_audio_sha256_by_key"]
                    or head not in DIMS or not isinstance(blob,bytes)
                    or len(blob)!=4*DIMS[head]
                    or audio!=plan["private_source_audio_sha256_by_key"][key]
                    or head in result.setdefault(key,{})):
                raise ValueError("Native 240 head shape, audio or identity mismatch")
            values=struct.unpack("<"+"f"*DIMS[head],blob)
            if any(not math.isfinite(v) for v in values):
                raise ValueError("Nonfinite native teacher scores")
            result[key][head]=values
    if set(result)!=set(keys) or any(set(item)!=set(DIMS) for item in result.values()):
        raise ValueError("Not exactly 240 complete native head pairs")
    # The 1280D output is used only for frozen representations/baselines.
    for key in keys:
        file=path.parent/"embeddings"/(hashlib.sha256(key.encode()).hexdigest()+".json")
        if not file.is_file():
            raise ValueError("Missing pooled 1280D vector")
        doc=_private_json(file)
        v=doc.get("vector_f32")
        if (doc.get("track_file")!=key or doc.get("dimension")!=1280
                or doc.get("audio_sha256")!=plan["private_source_audio_sha256_by_key"][key]
                or not isinstance(v,list) or len(v)!=1280
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in v)):
            raise ValueError("Embedding identity/provenance/dimension mismatch")
        if abs(math.sqrt(sum(float(x)*float(x) for x in v))-1)>1e-5:
            raise ValueError("Embedding not L2 normalized")
        result[key]["embedding"]=v
    return result


def _distance(np, x) -> list[float]:
    return [float(np.linalg.norm(x[i]-x[j]))
        for i in range(len(x)) for j in range(i+1,len(x))]


def _cosine_dissimilarities(np, x, *, center=None) -> list[float]:
    if center is not None:
        x=x-center
    norms=np.linalg.norm(x,axis=1)
    if not np.isfinite(norms).all() or (norms<1e-12).any():
        raise ValueError("Degenerate cosine baseline")
    y=x/norms[:,None]
    return [float(1-np.dot(y[i],y[j]))
            for i in range(len(y)) for j in range(i+1,len(y))]


def _finite_corr(x,y):
    if len(x)!=len(y) or len(x)!=N*(N-1)//2:
        raise ValueError("Expected all 28680 new-song pair distances")
    val=spearman(x,y)
    if val is None or not math.isfinite(val):
        raise ValueError("Undefined frozen Spearman association")
    return float(val)


def evaluate(plan_dir: Path, old_db: Path, bliss_db: Path,
             manifest_path: Path, protocol_path: Path) -> dict:
    contract=_private_json(protocol_path)
    if (contract.get("schema")!=PROTOCOL
            or contract.get("locked_before_new_240_essentia_inference") is not True
            or contract.get("development_songs")!=100
            or contract.get("source_identity_group_disjoint_future_songs")!=N
            or contract.get("hyperparameters",{}).get("no_tuning_on_new_teacher_or_human_labels") is not True
            or contract["hyperparameters"].get("moodtheme_teacher_dimensions")!=56):
        raise ValueError("Frozen evaluation protocol changed/incomplete")
    plan=_private_json(plan_dir/"private-scan-plan.json")
    if plan.get("schema")!=PLAN_SCHEMA or plan.get("songs")!=N:
        raise ValueError("R6 native scan plan invalid")
    if hashlib.sha256(old_db.read_bytes()).hexdigest()!=plan["old_grouped_db_sha256"]:
        raise ValueError("Old teacher development DB changed since native preparation")
    if hashlib.sha256(bliss_db.read_bytes()).hexdigest()!=plan["source_bliss_db_sha256"]:
        raise ValueError("Original Bliss DB changed since native preparation")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=plan["private_r5_manifest_sha256"]:
        raise ValueError("R5 exact selection changed since preparation")
    old,_=_old_grouped_rows(old_db)
    manifest=_private_json(manifest_path)
    keys,new_bliss=_load_new_bliss(bliss_db,manifest,{item[0] for item in old})
    if len(keys)!=N:
        raise ValueError("Wrong future cohort size")
    frozen_manifest=("".join(k+"\n" for k in sorted(keys))).encode()
    if hashlib.sha256(frozen_manifest).hexdigest()!=plan["manifest_sha256"]:
        raise ValueError("Native outputs do not match frozen R5 manifest")
    native=_native_rows(plan_dir/"native-features.sqlite",keys,plan)

    np, sklearn, PLSRegression,_,_,Ridge,make_pipeline,StandardScaler=_requires_sklearn()
    Xtrain=np.asarray([row[1] for row in old],dtype=np.float64)
    Ytrain=np.asarray([row[2] for row in old],dtype=np.float64)
    Xnew=np.asarray(new_bliss,dtype=np.float64)
    Ymood=np.asarray([native[k]["moodtheme"] for k in keys],dtype=np.float64)
    Ygenre=np.asarray([native[k]["genre"] for k in keys],dtype=np.float64)
    Emb=np.asarray([native[k]["embedding"] for k in keys],dtype=np.float64)
    if (Xtrain.shape!=(100,23) or Ytrain.shape!=(100,56)
            or Xnew.shape!=(N,23) or Ymood.shape!=(N,56)
            or Ygenre.shape!=(N,87) or Emb.shape!=(N,1280)):
        raise ValueError("Frozen feature dimensions not satisfied")
    # The old Genre87 PLS(2) comparator was also frozen BEFORE R6.
    old_genre = []
    with closing(sqlite3.connect(old_db.resolve().as_uri()+"?mode=ro",uri=True)) as c:
        c.execute("PRAGMA query_only=ON")
        for key, raw in c.execute(
                "SELECT track_key,genre_f32_le FROM paired_tracks "
                "ORDER BY track_key COLLATE BINARY"):
            if not isinstance(raw,bytes) or len(raw)!=87*4:
                raise ValueError("Previous 100 Genre teacher output dimensions wrong")
            old_genre.append((key,struct.unpack("<87f",raw)))
    if [key for key,_ in old_genre]!=[row[0] for row in old]:
        raise ValueError("Old development Genre and Bliss order incompatible")
    Yold_genre=np.asarray([row[1] for row in old_genre],dtype=np.float64)
    genre_mean=np.mean(Yold_genre,axis=0)
    genre_constant_mae=float(np.mean(np.abs(Ygenre-genre_mean)))
    genre_pls=make_pipeline(StandardScaler(),
         PLSRegression(n_components=2,max_iter=500,scale=True))
    genre_pls.fit(Xtrain,Yold_genre)
    genre_pred=genre_pls.predict(Xnew)
    if genre_pred.shape!=(N,87) or not np.isfinite(genre_pred).all():
        raise ValueError("Frozen Genre PLS produced invalid new-song outputs")
    genre_pls_mae=float(np.mean(np.abs(Ygenre-genre_pred)))
    # NO StandardScaler/Ridge fit on the NEW 240, ever.
    scaler=StandardScaler().fit(Xtrain)
    model=Ridge(alpha=10.0).fit(scaler.transform(Xtrain),Ytrain)
    prediction=model.predict(scaler.transform(Xnew))
    if not np.isfinite(prediction).all():
        raise ValueError("Invalid out-of-cohort Ridge predictions")
    # Constant baseline fitted on OLD 100 only; no student/alpha selection.
    mean=np.mean(Ytrain,axis=0)
    baseline=float(np.mean(np.abs(Ymood-mean)))
    mae=float(np.mean(np.abs(Ymood-prediction)))

    raw_dist=_distance(np,Xnew)
    scaled_dist=_distance(np,scaler.transform(Xnew))
    student_dist=_distance(np,prediction)
    mood_dist=_distance(np,Ymood)
    genre_dist=_distance(np,Ygenre)
    representations={
        "raw_bliss23_euclidean":raw_dist,
        "old_train_scaled_bliss23_euclidean":scaled_dist,
        "frozen_moodtheme_ridge_student_euclidean":student_dist,
        "genre87_cosine_dissimilarity":_cosine_dissimilarities(np,Ygenre),
        "moodtheme56_cosine_dissimilarity":_cosine_dissimilarities(np,Ymood),
        "moodtheme56_old_train_mean_centered_cosine_dissimilarity":
            _cosine_dissimilarities(np,Ymood,center=mean),
        "discogs_effnet_embedding1280_cosine_dissimilarity":_cosine_dissimilarities(np,Emb)
    }
    # All seven representations are evaluated on the SAME unordered pairs.
    # A pair is not an independent observation, ever.
    correlations={
        name:{
            "vs_moodteacher_euclidean":_finite_corr(series,mood_dist),
            "vs_genreteacher_euclidean":_finite_corr(series,genre_dist)
        } for name,series in representations.items()
    }
    return {
        "schema":"wp3-r6-frozen-independent-240-teacher-proxy-aggregate-v1",
        "status":"EXTERNAL_COHORT_TEACHER_PROXY_NOT_HUMAN_MUSICAL_VALIDATION",
        "new_songs":N,
        "group_disjoint_sources_per_frozen_r5_plan":True,
        "old_development_songs_used_to_fit":100,
        "old_25_group_holdout_reused_in_development":True,
        "frozen_ridge_alpha":10.0,
        "new_song_teacher_labels_used_in_fitting":False,
        "moodtheme_teacher_output_mae":{
            "train_mean_baseline":baseline,
            "bliss_only_fixed_ridge":mae,
            "relative_reduction":(baseline-mae)/baseline if baseline>0 else None
        },
        "genre_teacher_output_mae":{"train_mean_baseline":genre_constant_mae,
            "old_train_only_pls_2":genre_pls_mae,
            "relative_reduction":(genre_constant_mae-genre_pls_mae)/genre_constant_mae if genre_constant_mae>0 else None},
        "pairwise_spearman_to_teachers":correlations,
        "new_song_unordered_pairs":N*(N-1)//2,
        "pairwise_observations_statistically_independent":False,
        "reference_is_essentia_teacher_not_listener_judgment":True,
        "upstream_essentia_head_parity_independently_certified":False,
        "model_pretraining_overlap_certified_absent":False,
        "human_similarity_quality_measured":False,
        "WP1_and_WP2_winners_not_determined":True,
        "private_track_keys_or_vectors_in_aggregate":False
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan-dir",required=True,type=Path)
    p.add_argument("--old-grouped-research-db",required=True,type=Path)
    p.add_argument("--bliss-db",required=True,type=Path)
    p.add_argument("--r5-manifest",required=True,type=Path)
    p.add_argument("--frozen-protocol",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    try:
        if a.out.exists() or a.out.is_symlink():
            raise ValueError("Refuse existing aggregate")
        result=evaluate(a.plan_dir,a.old_grouped_research_db,a.bliss_db,
                        a.r5_manifest,a.frozen_protocol)
        with a.out.open("x",encoding="utf-8") as fp:
            json.dump(result,fp,indent=2,allow_nan=False)
            fp.write("\n")
        print(json.dumps({
            "schema":result["schema"],"status":result["status"],
            "new_songs":N,
            "teacher_proxy_evaluation_saved_private":True,
            "perceptual_similarity_not_evaluated":True
        },indent=2))
    except (ValueError,TypeError,KeyError,OSError,OverflowError,sqlite3.Error,RuntimeError):
        p.exit(2,"WP3 R6 frozen evaluation BLOCKED: native/Bliss/model/manifest "
                 "validation or complete 240 source data missing; no quality claim\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
