#!/usr/bin/env python3
"""WP3-R6: source-locked private 240-song original Essentia C++ scan.

prepare: rederive existing R5 exact-key manifest and freeze audio, classifier
metadata, original binary, C++ worker and source hashes in a NEW private
directory, without scanning.
verify: validate exact 240 native schema-v3 87D/56D/2D outputs and every
pooled 1280D embedding, audio/model provenance and frozen manifest.
Neither stage decodes or analyzes any audio, opens sources writable, changes
LMS, computes similarity quality, or prints private identities.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import struct
import sys

from prepare_wp3_independent_cohort import plan as derive_selection

N = 240
SOURCE_SEED = 20261030
EXPECTED_EXE_SHA = "00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d"
SCHEMA = "wp3-r6-native-240-plan-v1"
EMBED_POOL = "patch_f64_arithmetic_mean_v1"
EMBED_NORM = "song_f64_l2_then_cast_f32_v1"
MODELS = {
    "encoder": "discogs-effnet-bsdynamic-1.onnx",
    "genre": "mtg_jamendo_genre-discogs-effnet-1.onnx",
    "moodtheme": "mtg_jamendo_moodtheme-discogs-effnet-1.onnx",
    "voice": "voice_instrumental-discogs-effnet-1.onnx",
}
LABELS = {
    "genre": "mtg_jamendo_genre-discogs-effnet-1.json",
    "moodtheme": "mtg_jamendo_moodtheme-discogs-effnet-1.json",
    "voice": "voice_instrumental-discogs-effnet-1.json",
}
DIMS = {"genre":87,"moodtheme":56,"voice":2}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for blob in iter(lambda: source.read(1024*1024), b""):
            h.update(blob)
    return h.hexdigest()


def _private_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 8*1024*1024:
        raise ValueError("Private prerequisite is missing or too large")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict):
        raise ValueError("Malformed private JSON contract")
    return data


def _safe_track(key: str, root: Path) -> Path:
    if (not isinstance(key,str) or not key or len(key)>4000
            or "\\" in key or "\0" in key or "\n" in key or "\r" in key
            or key.startswith("/") or ":" in key
            or any(part in ("", ".", "..") for part in key.split("/"))):
        raise ValueError("Unsafe source-relative track key")
    base = root.resolve(strict=True)
    path = base.joinpath(*key.split("/")).resolve(strict=True)
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError("Audio file unavailable or escapes authorized root")
    return path


def _model_evidence(models: Path, old_db: Path) -> dict:
    if not models.is_dir():
        raise ValueError("Official model root missing")
    names = [*MODELS.values(),*LABELS.values()]
    hashes = {name:_hash(models/name) for name in names}
    for head,dim in DIMS.items():
        labels = _private_json(models/LABELS[head]).get("classes")
        if (not isinstance(labels,list) or len(labels)!=dim
                or any(not isinstance(v,str) or not v for v in labels)
                or len(set(labels))!=dim):
            raise ValueError("Wrong official model class order/shape")
    # The official encoder/head weights and class ordering must agree with
    # the original 100-song native development training teacher.
    with closing(sqlite3.connect(old_db.resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        evidence = {}
        for head in ("genre","moodtheme"):
            vals = db.execute("""
                SELECT DISTINCT m.embedding_model, m.classification_model,
                       m.models_sha256_json,m.classes_json
                FROM feature_models m
                JOIN feature_tracks t ON t.model_key=m.model_key
                WHERE t.model_id=?
            """,(head,)).fetchall()
            if len(vals)!=1:
                raise ValueError("Old native heads have ambiguous model evidence")
            encoder, classifier, model_hashes, class_json = vals[0]
            if encoder!=MODELS["encoder"] or classifier!=MODELS[head]:
                raise ValueError("Changed classifier/encoder model filenames")
            fingerprints=json.loads(model_hashes)
            if (fingerprints.get(encoder)!=hashes[encoder]
                    or fingerprints.get(classifier)!=hashes[classifier]):
                raise ValueError("Official weights differ from the original research cohort")
            if json.loads(class_json)!=_private_json(models/LABELS[head])["classes"]:
                raise ValueError("Official class order differs from old teacher")
            evidence[head]=True
    return hashes


def _manifest_selection(bliss: Path, snapshot: Path, library: Path, old: Path,
                        selected: Path) -> list[str]:
    actual = _private_json(selected)
    derived,_=derive_selection(bliss,snapshot,library,old,count=N,seed=SOURCE_SEED)
    if actual!=derived:
        raise ValueError("R5 private selection changed or sources drifted")
    keys = [x["track_file"] for x in derived["selected_songs"]]
    if len(keys)!=N or len(set(keys))!=N:
        raise ValueError("Expected exactly 240 unique selected tracks")
    return keys


def prepare(args) -> dict:
    if args.out_dir.exists() or args.out_dir.is_symlink():
        raise ValueError("Refuse to overwrite existing R6 output")
    if (args.source_root.resolve()==args.models_dir.resolve()
            or args.out_dir.resolve().is_relative_to(args.source_root.resolve())
            or args.out_dir.resolve().is_relative_to(args.models_dir.resolve())):
        raise ValueError("Private output must be outside music and model roots")
    keys=_manifest_selection(args.bliss_db,args.snapshot,args.library,
                             args.old_grouped_db,args.r5_manifest)
    audio_hashes={}
    for k in keys:
        audio_hashes[k]=_hash(_safe_track(k,args.source_root))
    if not args.scanner.is_file() or not args.worker.is_file():
        raise ValueError("Locally verified native scanner/worker missing")
    scanner_sha=_hash(args.scanner)
    if scanner_sha!=EXPECTED_EXE_SHA:
        raise ValueError("Refusing a scanner build different from the verified previous Windows binary")
    build=args.scanner.parent/"BUILD.txt"
    sums=args.scanner.parent/"SHA256SUMS.txt"
    if (not build.is_file() or not sums.is_file()
            or "da8fecee23930c2e52abcb473a62b8178b2d5474"
                not in build.read_text(encoding="utf-8-sig")
            or scanner_sha not in sums.read_text(encoding="utf-8-sig").lower()):
        raise ValueError("Scanner artifact source/build fingerprint not established")
    worker_sha=_hash(args.worker)
    dependency=args.worker.parent/"worker-dependencies.json"
    native=_private_json(dependency)
    files=native.get("files")
    if (native.get("schema_version")!=1 or not isinstance(files,dict)
            or args.worker.name.lower() not in files):
        raise ValueError("C++ native worker dependency manifest invalid")
    for filename,metadata in files.items():
        if (not re.fullmatch(r"[a-z0-9_.+-]+\.(?:exe|dll)",filename)
                or not isinstance(metadata,dict)
                or _hash(args.worker.parent/filename)!=metadata.get("sha256")):
            raise ValueError("Native worker dependency file hash mismatch")
    hashes=_model_evidence(args.models_dir,args.old_native_db)
    manifest=("".join(k+"\n" for k in sorted(keys))).encode("utf-8")
    fingerprint={
        "schema":SCHEMA,"status":"PREPARED_NO_AUDIO_SCAN_YET",
        "songs":N,"selection_seed":SOURCE_SEED,
        "manifest_sha256":hashlib.sha256(manifest).hexdigest(),
        "private_r5_manifest_sha256":_hash(args.r5_manifest),
        "old_grouped_db_sha256":_hash(args.old_grouped_db),
        "old_native_teacher_db_sha256":_hash(args.old_native_db),
        "source_bliss_db_sha256":_hash(args.bliss_db),
        "copied_snapshot_sha256":_hash(args.snapshot),
        "copied_library_sha256":_hash(args.library),
        "scanner_sha256":scanner_sha,"native_worker_sha256":worker_sha,
        "native_worker_dependencies_manifest_sha256":_hash(dependency),
        "official_model_files_sha256":hashes,
        "private_source_audio_sha256_by_key":audio_hashes,
        "expected_audio_backend":"essentia_cpp_original",
        "expected_models":["genre","moodtheme","voice"],
        "expected_embedding_dimensions":1280,
        "no_new_songs_used_for_student_fitting":True,
        "no_metric_selection_after_teacher_results":True,
        "teacher_output_is_not_perceptual_truth":True
    }
    args.out_dir.mkdir(parents=True,exist_ok=False)
    (args.out_dir/"embeddings").mkdir()
    (args.out_dir/"exact-240-tracks.txt").write_bytes(manifest)
    (args.out_dir/"private-scan-plan.json").write_text(
        json.dumps(fingerprint,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"schema":SCHEMA,"status":"READY_FOR_FROZEN_NATIVE_CPP_SCAN",
            "songs":N,"groups_disjoint_r5_against_old_reverified":True,
            "audio_source_files_hashed":N,"models_verified_against_old_teacher":True,
            "native_scanner_and_worker_verified":True,"scanned":False,
            "private_song_identifiers_in_stdout":False}


def _stored(plan: dict, name: str, path: Path) -> None:
    if _hash(path)!=plan[name]:
        raise ValueError("Frozen source or tool drift after preparation")


def verify(args) -> dict:
    folder=args.plan_dir
    plan=_private_json(folder/"private-scan-plan.json")
    if plan.get("schema")!=SCHEMA or plan.get("songs")!=N:
        raise ValueError("Wrong private plan")
    _stored(plan,"private_r5_manifest_sha256",args.r5_manifest)
    _stored(plan,"old_grouped_db_sha256",args.old_grouped_db)
    _stored(plan,"old_native_teacher_db_sha256",args.old_native_db)
    _stored(plan,"source_bliss_db_sha256",args.bliss_db)
    _stored(plan,"copied_snapshot_sha256",args.snapshot)
    _stored(plan,"copied_library_sha256",args.library)
    _stored(plan,"scanner_sha256",args.scanner)
    _stored(plan,"native_worker_sha256",args.worker)
    _stored(plan,"native_worker_dependencies_manifest_sha256",
            args.worker.parent/"worker-dependencies.json")
    for name,sha in plan["official_model_files_sha256"].items():
        if _hash(args.models_dir/name)!=sha:
            raise ValueError("Frozen model file changed")
    keys=_manifest_selection(args.bliss_db,args.snapshot,args.library,
                             args.old_grouped_db,args.r5_manifest)
    expected_manifest=("".join(k+"\n" for k in sorted(keys))).encode()
    if hashlib.sha256(expected_manifest).hexdigest()!=plan["manifest_sha256"]:
        raise ValueError("Private exact-key manifest changed")
    if (folder/"exact-240-tracks.txt").read_bytes()!=expected_manifest:
        raise ValueError("Output manifest not frozen")
    originals=plan["private_source_audio_sha256_by_key"]
    if set(originals)!=set(keys):
        raise ValueError("Frozen audio file list mismatched")
    for key in keys:
        if _hash(_safe_track(key,args.source_root))!=originals[key]:
            raise ValueError("Audio bytes changed after plan freeze")
    dbpath=folder/"native-features.sqlite"
    embeddings=folder/"embeddings"
    if not dbpath.is_file() or not embeddings.is_dir():
        raise ValueError("Native C++ outputs incomplete")
    if set(p.name for p in embeddings.iterdir()) != {
            hashlib.sha256(k.encode()).hexdigest()+".json" for k in keys}:
        raise ValueError("Pooled embedding directory incomplete or contains unexpected files")
    actual={}
    defs={}
    with closing(sqlite3.connect(dbpath.resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA user_version").fetchone()[0]!=3:
            raise ValueError("Native feature sidecar is not schema v3")
        for k,head,audio_sha,patches,blob,preprocessing,encoder,classifier,raw_sha,labels in db.execute("""
            SELECT t.track_file,t.model_id,t.audio_sha256,t.patches_analyzed,
                   t.scores_f32_le,m.preprocessing_version,m.embedding_model,
                   m.classification_model,m.models_sha256_json,m.classes_json
            FROM feature_tracks t JOIN feature_models m
            ON t.model_key=m.model_key
        """):
            if (k not in originals or head not in DIMS
                    or head in actual.setdefault(k,{})
                    or not isinstance(preprocessing,str)
                    or not preprocessing.startswith("experimental-essentia-cpp-dsp")
                    or audio_sha!=originals[k] or type(patches)!=int or patches<1
                    or not isinstance(blob,bytes) or len(blob)!=DIMS[head]*4
                    or encoder!=MODELS["encoder"]
                    or classifier!=MODELS[head]):
                raise ValueError("Native head source/provenance/dimension mismatch")
            floats=struct.unpack("<"+"f"*DIMS[head],blob)
            if not all(math.isfinite(x) and 0<=x<=1 for x in floats):
                raise ValueError("Native head has nonfinite/out-of-bounds scores")
            hashes=json.loads(raw_sha)
            if (hashes.get(encoder)!=plan["official_model_files_sha256"][encoder]
                    or hashes.get(classifier)!=plan["official_model_files_sha256"][classifier]
                    or hashes.get("essentia_cpp_worker_binary_sha256")
                    !=plan["native_worker_sha256"]
                    or json.loads(labels)!=_private_json(args.models_dir/LABELS[head])["classes"]):
                raise ValueError("Native head model hash/worker/label mismatch")
            defs.setdefault(head,set()).add((preprocessing,patches>0))
            actual[k][head]=(audio_sha,patches,preprocessing)
    if set(actual)!=set(keys) or any(set(v)!=set(DIMS) for v in actual.values()):
        raise ValueError("Native 240 head coverage is incomplete or contains extra tracks")
    if any(len({actual[k][h][1] for h in DIMS})!=1 or
           len({actual[k][h][2] for h in DIMS})!=1 for k in keys):
        raise ValueError("Native head patch/frontend identity disagreement")
    if len({actual[k]["genre"][2] for k in keys})!=1:
        raise ValueError("Mixed native C++ frontend versions")
    preprocessing=actual[keys[0]]["genre"][2]
    encoder_sha=plan["official_model_files_sha256"][MODELS["encoder"]]
    fp=hashlib.sha256(json.dumps([
        1,MODELS["encoder"],encoder_sha,preprocessing,EMBED_POOL,EMBED_NORM,1280
    ],ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    for k in keys:
        doc=_private_json(embeddings/(hashlib.sha256(k.encode()).hexdigest()+".json"))
        expected={"schema_version":1,"kind":"discogs_effnet_song_embedding",
           "validation_status":"experimental_unvalidated",
           "dimension":1280,"track_file":k,"audio_sha256":originals[k],
           "patches_analyzed":actual[k]["genre"][1],
           "encoder_model":MODELS["encoder"],"encoder_sha256":encoder_sha,
           "preprocessing_version":preprocessing,"pooling_version":EMBED_POOL,
           "normalization_version":EMBED_NORM,"representation_fingerprint":fp}
        if any(doc.get(key)!=val for key,val in expected.items()):
            raise ValueError("Pooled 1280D embedding provenance mismatch")
        vec=doc.get("vector_f32")
        if (not isinstance(vec,list) or len(vec)!=1280
                or any(type(x) not in (float,int) or not math.isfinite(x) for x in vec)
                or abs(math.sqrt(sum(float(x)*float(x) for x in vec))-1)>1e-5):
            raise ValueError("Pooled embedding invalid or not unit-normalized")
    return {"schema":"wp3-r6-native-240-validation-v1",
        "status":"FULL_240_CPP_GENRE_MOOD_VOICE_EMBEDDING_PROVENANCE_PASS",
        "exact_new_songs":N,"genre87":N,"moodtheme56":N,"voice2":N,
        "complete_pooled_embedding1280":N,"unchanged_audio_sha256":N,
        "native_cpp_frontend_verified":True,"previous_cohort_exact_disjoint":True,
        "model_sha256_consistent_with_previous_cohort":True,
        "head_numeric_parity_independently_certified":False,
        "teacher_training_overlap_ruled_out":False,
        "human_perceptual_similarity_quality_measured":False,
        "private_song_identities_in_aggregate":False}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","verify"))
    for opt in ("bliss-db","snapshot","library","old-grouped-db","old-native-db",
                "r5-manifest","source-root","models-dir","scanner","worker"):
        p.add_argument("--"+opt,required=True,type=Path)
    p.add_argument("--out-dir",type=Path,help="NEW private plan directory (prepare)")
    p.add_argument("--plan-dir",type=Path,help="EXISTING frozen plan directory (verify)")
    a=p.parse_args()
    try:
        if a.action=="prepare":
            if a.out_dir is None or a.plan_dir is not None:
                raise ValueError("Preparation requires only NEW out-dir")
            result=prepare(a)
        else:
            if a.plan_dir is None or a.out_dir is not None:
                raise ValueError("Verification requires only existing plan-dir")
            result=verify(a)
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,OverflowError,UnicodeError):
        p.exit(2,"WP3 R6 native 240 BLOCKED: source/model/native scan provenance or "
                   "complete 240 outputs unavailable; no metric gain certified\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
