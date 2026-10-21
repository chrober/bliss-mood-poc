#!/usr/bin/env python3
"""Export at most 100 research song embeddings from an existing v5 head cohort.

Local-only tool. Dry-run by default; explicit --execute is required.
Source music and schema-v3 feature DB are read-only; never overwrites exports.
No track identities, song vectors, audio paths or individual errors are printed.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

import audit_local_feature_readiness as readiness
import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import filename_for_key, validate_embedding

PINNED_SOURCE = "2c3d44401436b3b41b6e067199016a1ed2335fbf"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_file(root: Path, key: str) -> Path:
    """Resolve exact relative LMS song key without permitting traversal or UNC injection."""
    if (not key or "\\" in key or ":" in key or key.startswith("/") or "\0" in key
            or any(bit in ("", ".", "..") for bit in key.split("/"))):
        raise ValueError("Unsafe track key in local database")
    path = root.joinpath(*key.split("/")).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Song resolves outside the authorized local audio root") from exc
    if not path.is_file():
        raise FileNotFoundError("At least one selected local audio file is missing")
    return path


def model_sources(conn: sqlite3.Connection, cohorts: dict) -> dict[str, str]:
    expected: dict[str, str] = {}
    for meta in cohorts.values():
        row = conn.execute(
            """SELECT embedding_model, classification_model, models_sha256_json
               FROM feature_models WHERE model_key=?""",
            (meta["model_key"],),
        ).fetchone()
        if row is None:
            raise ValueError("Missing selected feature model metadata")
        encoder, classifier, raw_sha = row
        try:
            sha = json.loads(raw_sha)
        except (TypeError, ValueError) as exc:
            raise ValueError("Malformed local model provenance") from exc
        if not isinstance(sha, dict):
            raise ValueError("Malformed model SHA metadata")
        for name in (encoder, classifier):
            if (not isinstance(name, str) or not name or name != Path(name).name
                    or "/" in name or "\\" in name):
                raise ValueError("Unsafe model file name in SQLite metadata")
            digest = sha.get(name)
            if not isinstance(digest, str) or readiness.SHA256.fullmatch(digest) is None:
                raise ValueError("Missing official model SHA256 in SQLite metadata")
            if name in expected and expected[name] != digest.lower():
                raise ValueError("Conflicting model SHA256 between classification heads")
            expected[name] = digest.lower()
    if len(expected) != 3:
        raise ValueError("Expected shared encoder and exactly two distinct heads")
    return expected


def verify_local_binary(binary: Path) -> None:
    if not binary.is_file():
        raise FileNotFoundError("Experimental Windows research binary not found")
    build = binary.parent / "BUILD.txt"
    checksums = binary.parent / "SHA256SUMS.txt"
    if not build.is_file() or not checksums.is_file():
        raise ValueError("Use the complete verified research Windows binary artifact")
    meta = build.read_text(encoding="utf-8-sig")
    if f"Pinned Rust-v5 commit: {PINNED_SOURCE}" not in meta or "Research overlay commit:" not in meta:
        raise ValueError("Wrong research executable provenance; expected pinned Rust-v5 overlay")
    listed = checksums.read_text(encoding="ascii").splitlines()
    matching = [line.split()[0].lower() for line in listed
                if len(line.split()) == 2 and line.split()[1] == "*bliss-mood.exe"]
    if len(matching) != 1 or matching[0] != file_sha256(binary):
        raise ValueError("Research executable SHA256 mismatch")


def preflight(db: Path, audio_root: Path, models_dir: Path, binary: Path,
              *, limit: int = 100, seed: int = 20261021) -> list[tuple[str, Path, str, int, str]]:
    if not 1 <= limit <= 100:
        raise ValueError("Local export is deliberately capped at 100 songs")
    root = audio_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError("Private audio root does not exist")
    if not models_dir.is_dir():
        raise FileNotFoundError("Official local models directory not found")
    verify_local_binary(binary)
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise ValueError("ffmpeg and ffprobe must both be available in local PATH")
    with closing(ev.open_database(db)) as conn:
        cohorts = {head: ev._catalog(conn, head, experimental=True) for head in ev.MODELS}
        if {m["preprocessing_version"] for m in cohorts.values()} != {readiness.V5_PREPROCESSING}:
            raise ValueError("Expected corrected experimental Rust-v5 head cohorts")
        for name, digest in model_sources(conn, cohorts).items():
            p = models_dir / name
            if not p.is_file() or file_sha256(p) != digest:
                raise ValueError("Local official ONNX encoder/head hash mismatch")
        # Profile metadata is required by the classifier CLI but is not
        # itself a persisted head model hash. Do not equate it with validated parity.
        for head in ("genre", "moodtheme"):
            model_name = conn.execute(
                "SELECT classification_model FROM feature_models WHERE model_key=?",
                (cohorts[head]["model_key"],),
            ).fetchone()[0]
            if not (models_dir / (Path(model_name).stem + ".json")).is_file():
                raise FileNotFoundError("Required official classifier label JSON is missing")
        sample = ev.load_sample(conn, cohorts, limit, seed)
        if sample["sample_size"] != limit:
            raise ValueError("Insufficient compatible song pairs in local v5 cohort")
        items = []
        for key in sample["tracks"]:
            src = readiness.provenance(conn, key, cohorts)
            if src is None:
                raise ValueError("Incompatible original per-song head provenance")
            audio_sha, patches, encoder_sha = src
            file = source_file(root, key)
            if file_sha256(file) != audio_sha:
                raise ValueError("At least one source audio file changed since feature extraction")
            items.append((key, file, audio_sha, patches, encoder_sha))
        return items


def existing_embedding(path: Path, key: str, audio_sha: str, patches: int,
                       encoder_sha: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_embedding(
        data, key, audio_sha, patches, encoder_sha, readiness.V5_PREPROCESSING, None
    )


def export(db: Path, audio_root: Path, models_dir: Path, binary: Path,
           out_dir: Path, *, limit: int, seed: int, execute: bool,
           resume: bool = False) -> dict:
    if resume and not execute:
        raise ValueError("--resume requires --execute")
    out = out_dir.resolve()
    root = audio_root.resolve()
    if out == root or out.is_relative_to(root):
        raise ValueError("Research exports must be outside the music library")
    if out == models_dir.resolve():
        raise ValueError("Research exports must not overwrite the models folder")
    if execute and out.exists() and not resume:
        raise FileExistsError("Export directory already exists; use a new folder or explicit --resume")
    if resume and not out.is_dir():
        raise FileNotFoundError("Cannot resume: export directory does not exist")
    # Full independent model/recording SHA preflight BEFORE any write.
    items = preflight(db, audio_root, models_dir, binary, limit=limit, seed=seed)
    summary = {
        "schema": "local-1280d-research-export-aggregate-v1",
        "status": "dry_run_verified_no_changes" if not execute else "export_started",
        "sample_count": len(items), "audio_sha_verified": len(items),
        "model_files_sha_verified": 3,
        "existing_valid": 0, "exported_and_verified": 0,
        "failed": 0, "no_existing_sqlite_changes": True,
        "never_upload_private_audio_or_vectors": True,
    }
    if not execute:
        return summary
    if not resume:
        out.mkdir(parents=True, exist_ok=False)
    for key, file, audio_sha, patches, encoder_sha in items:
        target = out / filename_for_key(key)
        if target.exists():
            try:
                existing_embedding(target, key, audio_sha, patches, encoder_sha)
            except (ValueError, OSError, TypeError, KeyError):
                summary["failed"] += 1
            else:
                summary["existing_valid"] += 1
            continue
        result = subprocess.run(
            [str(binary), "analyze-features", str(file), "--models-dir",
             str(models_dir), "--models", "moodtheme,genre", "--threads", "1",
             "--json", "--track-key", key, "--embedding-out", str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
        )
        if result.returncode != 0 or not target.is_file():
            summary["failed"] += 1
            continue
        try:
            existing_embedding(target, key, audio_sha, patches, encoder_sha)
        except (ValueError, OSError, TypeError, KeyError):
            summary["failed"] += 1
        else:
            summary["exported_and_verified"] += 1
    summary["status"] = (
        "complete_verified" if summary["failed"] == 0 and
        summary["exported_and_verified"] + summary["existing_valid"] == len(items)
        else "incomplete_do_not_use_for_scoring"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--execute", action="store_true",
                        help="Opt in to decode/infer only these songs, never write SQLite")
    parser.add_argument("--resume", action="store_true",
                        help="Explicitly reuse a previous partial output folder; refuse invalid existing JSON")
    args = parser.parse_args()
    try:
        result = export(args.db, args.audio_root, args.models_dir, args.binary,
                        args.out_dir, limit=args.limit, seed=args.seed,
                        execute=args.execute, resume=args.resume)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result["failed"] else 0
    except (OSError, ValueError, sqlite3.DatabaseError) as error:
        # Intentionally never print paths, track keys or per-song stderr.
        parser.exit(2, f"Local research export stopped by preflight: {type(error).__name__}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
