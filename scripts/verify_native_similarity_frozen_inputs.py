#!/usr/bin/env python3
"""Read-only verification of an EXISTING frozen 100-song plan before native scan.

This never invokes prepare, creates a manifest, selects a replacement cohort, or
writes files. Its source comparisons use the existing cohort bridge invariants.
Only anonymized status is printed (no private song names, paths or vectors).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import native_similarity_cohort_bridge as bridge


def verify(plan_dir: Path, baseline_db: Path, baseline_embeddings: Path,
           models_dir: Path, audio_root: Path) -> dict:
    plan = json.loads((plan_dir / "provenance.json").read_text(encoding="utf-8"))
    if (plan.get("schema") != "native_similarity_cohort_bridge_v1"
            or plan.get("status") != "PREFLIGHT_VERIFIED_NO_NATIVE_SCAN_YET"
            or plan.get("tracks") != bridge.N):
        raise ValueError("Invalid frozen preflight provenance")
    manifest = (plan_dir / "exact-100-tracks.txt").read_bytes()
    if hashlib.sha256(manifest).hexdigest() != plan["source_manifest_sha256"]:
        raise ValueError("Frozen manifest checksum mismatch")
    if bridge.digest(baseline_db) != plan["old_sqlite_sha256"]:
        raise ValueError("Frozen Rust-v5 SQLite checksum mismatch")

    tracks, definitions = bridge.checked_stage(
        "verify_frozen_old_cohort", bridge.read_cohort,
        baseline_db, {"genre", "moodtheme"}, bridge.OLD_FRONTEND)
    expected = "".join(key + "\n" for key in sorted(tracks)).encode("utf-8")
    if expected != manifest:
        raise ValueError("Frozen manifest differs from verified cohort")
    representations = bridge.checked_stage(
        "verify_original_100_embeddings", bridge.validate_embeddings,
        baseline_embeddings, tracks, definitions)
    if len(representations) != bridge.N:
        raise ValueError("Incorrect original embedding coverage")
    model_hashes = bridge.checked_stage(
        "verify_frozen_model_weights_and_labels",
        bridge.validate_model_files, models_dir, definitions)
    if model_hashes != plan["model_file_sha256"]:
        raise ValueError("Frozen model metadata/hash mismatch")
    # This is an integrity gate on the EXISTING manifest, not a new preflight.
    # Audio is only opened read-only, and the original cohort stays unchanged.
    bridge.check_audio_sources(tracks, audio_root)
    return {
        "status": "FROZEN_INPUTS_REVERIFIED_READ_ONLY",
        "tracks": bridge.N,
        "manifest_sha256": plan["source_manifest_sha256"],
        "baseline_db_sha256_unchanged": True,
        "embedding_exports": len(representations),
        "audio_sha256_matches": bridge.N,
        "model_files_match_preflight": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan-dir", type=Path, required=True)
    p.add_argument("--baseline-db", type=Path, required=True)
    p.add_argument("--baseline-embeddings", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, required=True)
    p.add_argument("--audio-root", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(verify(**vars(args)), indent=2), flush=True)
        return 0
    except Exception as exc:
        # Never display a private path or unvalidated exception message.
        reason = exc.reason if isinstance(exc, bridge.BridgeStageError) else type(exc).__name__
        print("Frozen input integrity gate FAILED: " + reason, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
