#!/usr/bin/env python3
"""WP2-P3: opt-in, pinned executable may read ONLY a verified train-only bundle.

Run the EXISTING, unmodified Rust bliss-learner on the prepared private input.
No shell, network notifications, production bliss.db, holdout triplets, user
uploads or automatic release downloads. An operator must explicitly provide
the binary location and independently trusted exact SHA256. No model-quality
or General/Personal calibration claim.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from audit_bliss_essentia_join import open_bliss, bliss_vector
import subprocess
import sys

from research_personal_triplet_protocol import frozen_matrix
from prepare_bliss_learner_train_only import _sha256, _write_new

HEX64=re.compile(r"^[a-fA-F0-9]{64}$")


def run_verified(
    bundle_dir: Path, learner_exe: Path, expected_learner_sha256: str,
    out_dir: Path, *, timeout_seconds: int = 3600,
) -> dict:
    if (not HEX64.fullmatch(expected_learner_sha256)
            or type(timeout_seconds) is not int or not 30 <= timeout_seconds <= 86400):
        raise ValueError("Pinned executable digest and bounded timeout required")
    private_manifest=bundle_dir/"train-only-manifest-private.json"
    db=bundle_dir/"train-only-bliss.db"
    votes=bundle_dir/"train-only-triplets.json"
    if (not private_manifest.is_file() or not db.is_file()
            or not votes.is_file() or not learner_exe.is_file()
            or private_manifest.is_symlink() or db.is_symlink()
            or votes.is_symlink()):
        raise ValueError("Missing full isolated training bundle or exact learner executable")
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Refuse existing learner output directory")
    meta=json.loads(private_manifest.read_text(encoding="utf-8"))
    if (not isinstance(meta,dict)
            or meta.get("schema")!="lyrion_train_only_legacy_bliss_learner_bundle_private_v1"
            or meta.get("status")!="NOT_TRAINED__TRAIN_ONLY_STAGING"
            or meta.get("upstream_learner_final_matrix_trained_only_on_staged_train_subset") is not True
            or type(meta.get("train_triplet_count")) is not int
            or meta["train_triplet_count"] < 5):
        raise ValueError("Incompatible private train-only provenance")
    hashes={db:_sha256(db),votes:_sha256(votes),learner_exe:_sha256(learner_exe)}
    if (hashes[db].lower()!=meta.get("train_only_db_sha256","").lower()
            or hashes[votes].lower()!=meta.get("train_triplets_sha256","").lower()
            or hashes[learner_exe].lower()!=expected_learner_sha256.lower()):
        raise ValueError("Source bundle or pinned learner binary SHA256 differs")
    # Reinspect the exact source triple count and strictly local 23-feature DB.
    try:
        records=json.loads(votes.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid isolated training triplets") from exc
    if (not isinstance(records,list)
            or len(records)!=meta["train_triplet_count"]
            or any(not isinstance(x,list) or len(x)!=3
                   or len(set(x))!=3 or
                   not all(isinstance(s,str) and bool(s) for s in x)
                   for x in records)):
        raise ValueError("Private train-only triplet content inconsistent")
    # A forged manifest or misdirected bundle must not let the learner
    # read a full Bliss library. Require the complete staged DB song set
    # to equal the train-only triplet universe, with no extra rows.
    training_songs={key for triple in records for key in triple}
    if (len(training_songs)!=meta.get("training_track_count")
            or hashlib.sha256(json.dumps(sorted(training_songs),
                ensure_ascii=False).encode("utf-8")).hexdigest()
                    !=meta.get("train_track_keys_sha256")):
        raise ValueError("Training keys differ from pinned private manifest")
    with closing(open_bliss(db)) as conn:
        all_files=conn.execute("SELECT File FROM TracksV2").fetchall()
        if len(all_files)!=len(training_songs) or {row[0] for row in all_files}!=training_songs:
            raise ValueError("Staged Bliss DB includes missing or non-training songs")
        for key in training_songs:
            status,_=bliss_vector(conn,key)
            if status!="valid":
                raise ValueError("Staged learner DB has missing or invalid Bliss 23D")
    # The training staging verifier must be the only source; reject
    # unknown output file and never print paths, keys or subprocess streams.
    out_dir.mkdir(parents=False,exist_ok=False,mode=0o700)
    model=out_dir/"learned_matrix.json"
    command=[
        str(learner_exe.resolve()),
        "--db",str(db.resolve()),
        "--triplets",str(votes.resolve()),
        "--output",str(model.resolve()),
        # Deliberately omit --notifs so no Lyrion JSON-RPC is contacted.
    ]
    try:
        finished=subprocess.run(command,check=False,cwd=out_dir,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Pinned learner failed or timed out") from exc
    if finished.returncode!=0 or not model.is_file() or model.stat().st_size>4*1024*1024:
        raise ValueError("Learner failed or produced no bounded matrix JSON")
    # No overriding source files or executable during training, including
    # if another process attempted mutation (detect after run, fail closed).
    if any(_sha256(path)!=sha for path,sha in hashes.items()):
        raise ValueError("Training inputs or executable changed during learner run")
    raw=json.loads(model.read_text(encoding="utf-8"))
    frozen_matrix(raw) # structural, numeric, symmetry and PSD sanity; not training validity.
    result={
        "schema":"lyrion_train_only_learner_run_private_v1",
        "status":"TRAIN_ONLY_MATRIX_PRODUCED_NOT_INDEPENDENTLY_VALIDATED",
        "input_staging_manifest_sha256":_sha256(private_manifest),
        "train_triplets_sha256":hashes[votes],
        "train_only_db_sha256":hashes[db],
        "pinned_executable_sha256":hashes[learner_exe],
        "output_matrix_sha256":_sha256(model),
        "training_triplets":len(records),
        "no_holdout_triplet_file_passed":True,
        "lms_notifications_disabled":True,
        "learner_source_commit_not_automatically_certified":True,
        "learner_internal_cv_is_not_artist_album_grouped":True,
        "holdout_accuracy_not_yet_measured":True,
        "calibration_or_personal_blend_quality_not_proven":True,
        "private_bundle_must_never_be_published":True,
    }
    _write_new(out_dir/"learner-run-manifest-private.json",result)
    # Return only nonidentifying counts and flags to stdout/caller.
    return {
        "schema":result["schema"],
        "status":result["status"],
        "training_triplets":len(records),
        "matrix_verified_structural_numeric_only":True,
        "heldout_evaluation_not_run":True,
        "private_run_manifest_created":True,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle-dir",required=True,type=Path)
    p.add_argument("--learner-exe",required=True,type=Path)
    p.add_argument("--expected-learner-sha256",required=True)
    p.add_argument("--output-dir",required=True,type=Path)
    p.add_argument("--timeout-seconds",type=int,default=3600)
    a=p.parse_args()
    try:
        output=run_verified(a.bundle_dir,a.learner_exe,
                            a.expected_learner_sha256,a.output_dir,
                            timeout_seconds=a.timeout_seconds)
        print(json.dumps(output,indent=2))
    except (ValueError,TypeError,KeyError,OSError,sqlite3.Error,RuntimeError):
        p.exit(2,"Training blocked: verify isolated input hashes, executable "
                 "provenance and new output directory; no personal score was certified\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
