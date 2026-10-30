#!/usr/bin/env python3
"""WP3-R6: PRIVATE, blind original Bliss vs frozen MoodTheme Ridge student pilot.

Read-only genuine grouped 100-song WP3 research SQLite + untouched 240-song
candidate manifest + private original Bliss23 SQLite. Re-run exact cohort
selection against genuine copied Lyrion/Lab source SQLite before scoring.
Fit student on prior 100 DEVELOPMENT songs only, never on future cohort
teacher outputs, listener ratings, or audio. Outputs a sealed private audit,
private fitted model and optionally reviewable pair CSV with BLANK labels.
No musical quality, Lyrion queue change, or production model is claimed.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import struct
import sys

from audit_bliss_essentia_join import BLISS_COLUMNS, open_bliss, bliss_vector
from prepare_wp3_independent_cohort import plan as independent_plan
from research_bliss_essentia_teacher_models import _requires_sklearn

SCHEMA = "wp3-blind-student-vs-bliss-pilot-v1"
FIXED_SEED = 20261030
FIXED_COUNT = 24
STRATA = {"raw_prefers":6, "student_prefers":6, "random":12}
OLD_SCHEMA = "lyrion-wp3-research-snapshot-v1"
MANIFEST_SCHEMA = "wp3-independent-cohort-plan-v1"
SPEC_SCHEMA = "wp3-frozen-hypothesis-spec-v1"


def _json(path: Path, max_size: int) -> dict:
    if not path.is_file() or path.stat().st_size > max_size:
        raise ValueError("Required private JSON input missing or excessive")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def _old_grouped_rows(path: Path) -> tuple[list[tuple], str]:
    if not path.is_file():
        raise ValueError("Existing verified grouped research SQLite is required")
    rows = []
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Unsupported old grouped research DB version")
        md = dict(db.execute("SELECT key,value FROM metadata"))
        if md.get("schema") != OLD_SCHEMA or md.get("group_readiness") != "READY":
            raise ValueError("Old research DB not identity-group READY")
        metadata = json.loads(md["selection_json"])
        if int(metadata["sample_seed"]) != 20261029:
            raise ValueError("Unknown previous research cohort selection")
        if (metadata["chosen_head_model_ids"]["moodtheme"]["validated_against_essentia"]
                is not False):
            raise ValueError("Unexpected upstream teacher validation status")
        for key, bliss, mood, artist, album, rec in db.execute(
                "SELECT track_key,bliss_f64_le,moodtheme_f32_le,"
                "artist_group,album_group,recording_group "
                "FROM paired_tracks ORDER BY track_key COLLATE BINARY"):
            if (not isinstance(key,str) or not key or "\0" in key
                    or not isinstance(bliss,bytes) or len(bliss)!=23*8
                    or not isinstance(mood,bytes) or len(mood)!=56*4
                    or any(not isinstance(v,str) or not v.strip()
                           for v in (artist,album,rec))):
                raise ValueError("Malformed grouped development source row")
            x = struct.unpack("<23d", bliss)
            y = struct.unpack("<56f", mood)
            if not all(math.isfinite(z) for z in (*x,*y)):
                raise ValueError("Nonfinite old student training features")
            rows.append((key,x,y))
    if len(rows) != 100 or len({x[0] for x in rows}) != len(rows):
        raise ValueError("Frozen prior development cohort must have exactly 100 unique songs")
    return rows, hashlib.sha256(path.read_bytes()).hexdigest()


def _load_new_bliss(db_path: Path, manifest: dict, old_keys: set[str]):
    track_keys = []
    if (manifest.get("schema") != MANIFEST_SCHEMA
            or manifest.get("status") != "PRIVATE_CANDIDATE_PROPOSAL_NO_AUDIO_OR_HUMAN_VALIDATION"
            or manifest.get("seed") != FIXED_SEED
            or manifest.get("requested_new_songs") != 240
            or len(manifest.get("selected_songs",[])) != 240):
        raise ValueError("New candidate manifest identity/config mismatch")
    for row in manifest["selected_songs"]:
        key = row.get("track_file")
        if (not isinstance(key,str) or not key or "\0" in key
                or key in old_keys):
            raise ValueError("Future cohort contains prior or malformed song")
        track_keys.append(key)
    if len(set(track_keys)) != 240:
        raise ValueError("Duplicate songs in independent candidate manifest")
    vectors = []
    with closing(open_bliss(db_path)) as b:
        for key in track_keys:
            status, values = bliss_vector(b,key)
            if status != "valid":
                raise ValueError("Future cohort Bliss source changed or is ambiguous")
            vectors.append(values)
    return track_keys, vectors


def _rank(values: list[float]) -> list[int]:
    # Stable rank only; if ties in distances, tie break by pair index.
    ranks = [0]*len(values)
    for rank,i in enumerate(sorted(range(len(values)),key=lambda i:(values[i],i))):
        ranks[i]=rank
    return ranks


def _select_pairs(raw: list[float], student: list[float], n_songs: int,
                  *, seed: int = FIXED_SEED) -> tuple[list[dict],dict]:
    pool = list(itertools.combinations(range(n_songs),2))
    if len(pool) != len(raw) or len(raw) != len(student):
        raise ValueError("Pairwise vector lengths inconsistent")
    if any(not math.isfinite(v) for v in raw+student):
        raise ValueError("Non-finite pair distances")
    r_raw, r_student = _rank(raw), _rank(student)
    difference = [a-b for a,b in zip(r_raw,r_student)]
    # Positive delta = student is closer than raw (better student rank).
    rng = random.Random(seed)
    rankings = {
        "raw_prefers":sorted(range(len(pool)),key=lambda i:(difference[i],i)),
        "student_prefers":sorted(range(len(pool)),key=lambda i:(-difference[i],i)),
        "random":list(range(len(pool))),
    }
    rng.shuffle(rankings["random"])
    selected,used_pairs,used_songs=[],set(),set()
    # Exact 6/6/12 strata, disjoint songs so no single recording is
    # repeated in this limited descriptive diagnostic pilot.
    for stratum, quota in STRATA.items():
        for i in rankings[stratum]:
            a,b=pool[i]
            if i in used_pairs or a in used_songs or b in used_songs:
                continue
            selected.append({"stratum":stratum,"index":i,"left":a,"right":b,
                             "raw_rank":r_raw[i],"student_rank":r_student[i],
                             "raw_distance":raw[i],"student_distance":student[i]})
            used_pairs.add(i)
            used_songs.add(a)
            used_songs.add(b)
            if sum(row["stratum"]==stratum for row in selected)==quota:
                break
        else:
            raise ValueError("Unable to form independent listening pairs for every stratum")
    if len(selected)!=FIXED_COUNT or len(used_songs)!=2*FIXED_COUNT:
        raise ValueError("Incorrect blind sample or repeated source song")
    rng.shuffle(selected)
    result=[]
    for serial,row in enumerate(selected,1):
        left,right=row["left"],row["right"]
        if rng.getrandbits(1):
            left,right=right,left
        result.append(dict(row,pair_number=serial,left=left,right=right))
    return result, {
        "possible_unordered_pairs":len(pool),
        "selected_pairs":len(result),
        "distinct_song_count":len(used_songs),
        "selection_quotas":dict(STRATA),
        "selected_strata":{name:sum(x["stratum"]==name for x in result)
                           for name in STRATA},
    }


def make_outputs(bliss: Path, metadata_snapshot: Path, library: Path,
                 old_db: Path, manifest_path: Path, spec_path: Path, *,
                 seed: int = FIXED_SEED) -> tuple[list[dict],dict,dict,dict]:
    if seed != FIXED_SEED:
        raise ValueError("Only preregistered sampling seed accepted")
    spec = _json(spec_path, 100_000)
    c = spec.get("candidate",{})
    if (spec.get("schema")!=SPEC_SCHEMA
            or spec.get("status")!="EXPLORATORY_ARCHITECTURE_ONLY_NOT_TRAINED_MODEL"
            or c.get("teacher_head")!="moodtheme"
            or c.get("teacher_dimensions")!=56
            or c.get("input_feature_count")!=23
            or c.get("ridge_alpha")!=10):
        raise ValueError("Frozen hypothesis mismatch")
    manifest=_json(manifest_path,8*1024*1024)
    # Re-derive private identifiers from all source data and ensure the
    # manifest was not modified or borrowed from a different library.
    regenerated,_ = independent_plan(
        bliss,metadata_snapshot,library,old_db,count=240,seed=FIXED_SEED)
    if manifest != regenerated:
        raise ValueError("Future cohort manifest does not match current original sources")
    old, old_hash=_old_grouped_rows(old_db)
    keys, future = _load_new_bliss(bliss,manifest,{row[0] for row in old})

    np,sklearn,_,_,_,Ridge,_,StandardScaler=_requires_sklearn()
    X=np.asarray([row[1] for row in old],dtype=np.float64)
    Y=np.asarray([row[2] for row in old],dtype=np.float64)
    new=np.asarray(future,dtype=np.float64)
    if X.shape!=(100,23) or Y.shape!=(100,56) or new.shape!=(240,23):
        raise ValueError("Unexpected frozen group and future input dimensions")
    scaler=StandardScaler().fit(X)
    ridge=Ridge(alpha=10.0).fit(scaler.transform(X),Y)
    embedded=ridge.predict(scaler.transform(new))
    if embedded.shape!=(240,56) or not np.isfinite(embedded).all():
        raise ValueError("Nonfinite or malformed student inference on new cohort")
    raw_d, student_d=[],[]
    for a,b in itertools.combinations(range(len(keys)),2):
        raw_d.append(float(np.linalg.norm(new[a]-new[b])))
        student_d.append(float(np.linalg.norm(embedded[a]-embedded[b])))
    pairs, summary=_select_pairs(raw_d,student_d,len(keys),seed=seed)

    # Only local private files contain model coefficients or original keys.
    model={
        "schema":"wp3-private-ridge-student-parameters-v1",
        "frozen_spec_sha256":hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "old_grouped_research_sha256":old_hash,
        "training_dataset":"previous_100_grouped_development_songs",
        "original_25_group_holdout_reused_for_full_development_fit":True,
        "old_group_model_teacher_validation_certified":False,
        "future_new_songs_fitted":False,
        "numpy_version":np.__version__,"sklearn_version":sklearn.__version__,
        "feature_names_in_order":list(BLISS_COLUMNS),
        "teacher_head":"moodtheme",
        "teacher_dimensions":56,
        "ridge_alpha":10.0,
        "scaler_mean":scaler.mean_.tolist(),
        "scaler_scale":scaler.scale_.tolist(),
        "coef":ridge.coef_.tolist(),
        "intercept":ridge.intercept_.tolist(),
        "not_production_or_perceptually_validated":True,
    }
    audit={
        "schema":"wp3-private-sealed-blind-pilot-audit-v1",
        "selection_uses_comparison_model_distance_disagreement":True,
        "sampling_not_population_representative":True,
        "sampling_strata":STRATA,
        "seed":seed,
        "candidate_count":len(keys),
        "proposed_pairs":[{
            "pair_number":p["pair_number"],
            "left":keys[p["left"]],
            "right":keys[p["right"]],
            "sampling_stratum_keep_sealed":p["stratum"],
            "original_bliss_euclidean":p["raw_distance"],
            "student_moodtheme_euclidean":p["student_distance"],
            "original_rank":p["raw_rank"],
            "student_rank":p["student_rank"]
        } for p in pairs],
        "warning":"Keep sealed until independent human review, never infer labels from scores.",
    }
    rows=[{
        "pair_number":p["pair_number"],
        "left":keys[p["left"]],
        "right":keys[p["right"]],
        "similarity_0_to_5":"",
        "comments":""
    } for p in pairs]
    aggregate={
        "schema":SCHEMA,
        "status":"BLIND_PRIVATE_PAIR_PILOT_READY_NOT_HUMAN_EVALUATED",
        "old_development_songs":len(old),
        "old_group_holdout_reused_for_refit":True,
        "new_source_disjoint_songs":len(keys),
        "student_teacher_inference_on_new_songs":False,
        "student_inference_from_bliss_only":True,
        "new_audio_or_onnx_scans":False,
        "independent_perceptual_labels_available":False,
        "selected_blind_pairs":summary["selected_pairs"],
        "distinct_song_count":summary["distinct_song_count"],
        "possible_unordered_pairs":summary["possible_unordered_pairs"],
        "sampling_strata_counts":summary["selected_strata"],
        "blind_sample_is_unbiased_population_estimate":False,
        "model_fits_on_old_songs_only":True,
        "source_melody_artist_audio_byte_identity_certified":False,
        "private_song_keys_or_model_parameters_in_stdout":False,
    }
    return rows,model,audit,aggregate


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bliss-db",type=Path,required=True)
    p.add_argument("--repeat-identity-db",type=Path,required=True)
    p.add_argument("--lyrion-library-db",type=Path,required=True)
    p.add_argument("--old-grouped-research-db",type=Path,required=True)
    p.add_argument("--new-private-manifest",type=Path,required=True)
    p.add_argument("--frozen-spec",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.out_dir.exists() or a.out_dir.is_symlink():
            raise ValueError("Do not overwrite any private blind pilot output")
        rows,model,audit,aggregate=make_outputs(
            a.bliss_db,a.repeat_identity_db,a.lyrion_library_db,
            a.old_grouped_research_db,a.new_private_manifest,a.frozen_spec)
        a.out_dir.mkdir(parents=True,exist_ok=False)
        # No source write. Outputs are PRIVATE, each with exclusive new creation.
        with (a.out_dir/"private-blind-pairs.csv").open("x",encoding="utf-8-sig",
                  newline="") as fp:
            w=csv.DictWriter(fp,fieldnames=[
                "pair_number","left","right","similarity_0_to_5","comments"])
            w.writeheader()
            w.writerows(rows)
        with (a.out_dir/"private-frozen-student.json").open("x",
                encoding="utf-8") as fp:
            json.dump(model,fp,ensure_ascii=False,indent=2,allow_nan=False)
            fp.write("\n")
        with (a.out_dir/"private-sealed-selection-audit.json").open("x",
                encoding="utf-8") as fp:
            json.dump(audit,fp,ensure_ascii=False,indent=2,allow_nan=False)
            fp.write("\n")
        print(json.dumps(aggregate,indent=2,allow_nan=False))
    except (OSError,ValueError,TypeError,KeyError,OverflowError,sqlite3.Error,RuntimeError):
        p.exit(2,"WP3 blind pilot BLOCKED: source/provenance/candidate or "
               "frozen hypothesis mismatch; no evaluation result certified\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
