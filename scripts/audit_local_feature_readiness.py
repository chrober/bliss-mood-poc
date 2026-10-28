#!/usr/bin/env python3
"""Bounded, read-only LOCAL schema-v3 feature readiness report for Lyrion M1.

No scanning, audio access, song names/IDs in the output, score optimization,
SQLite writes, playlist changes, or upload of user data. Python stdlib only.
Research-only: valid extraction metadata is NOT production model validation.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys

import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import filename_for_key, validate_embedding

V5_PREPROCESSING = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_SAMPLE = 300


def provenance(conn: sqlite3.Connection, key: str, cohorts: dict) -> tuple[str, int, str] | None:
    """Return shared (audio SHA, patch count, encoder SHA) only if both heads agree."""
    rows = conn.execute(
        """SELECT f.model_id, f.model_key, f.audio_sha256, f.patches_analyzed,
                  m.embedding_model, m.classification_model, m.models_sha256_json,
                  m.preprocessing_version, m.aggregation
           FROM feature_tracks f JOIN feature_models m ON f.model_key = m.model_key
           WHERE f.track_file = ? COLLATE BINARY
             AND f.model_id IN ('genre', 'moodtheme')""", (key,),
    ).fetchall()
    if len(rows) != 2 or {r[0] for r in rows} != {"genre", "moodtheme"}:
        return None
    if any(r[1] != cohorts[r[0]]["model_key"] or
           r[7] != V5_PREPROCESSING or r[8] != ev.AGGREGATION
           for r in rows):
        return None
    audios, patches, encoders, encoding_models = set(), set(), set(), set()
    for _, _, audio, patch_count, encoder, classifier, sha_json, _, _ in rows:
        if not isinstance(audio, str) or not SHA256.fullmatch(audio):
            return None
        if not isinstance(patch_count, int) or patch_count <= 0:
            return None
        if not isinstance(encoder, str) or not encoder or not isinstance(classifier, str):
            return None
        try:
            shas = json.loads(sha_json)
        except (TypeError, ValueError):
            return None
        if not isinstance(shas, dict) or not all(
            isinstance(shas.get(m), str) and SHA256.fullmatch(shas[m])
            for m in (encoder, classifier)
        ):
            return None
        audios.add(audio.lower())
        patches.add(patch_count)
        encoders.add(shas[encoder].lower())
        encoding_models.add(encoder)
    if any(len(x) != 1 for x in (audios, patches, encoders, encoding_models)):
        return None
    return next(iter(audios)), next(iter(patches)), next(iter(encoders))


def report(db: Path, embedding_dir: Path | None, *, limit: int, seed: int) -> dict:
    if not 1 <= limit <= MAX_SAMPLE:
        raise ValueError("Local audit sample size must be 1..300")
    if embedding_dir is not None and not embedding_dir.is_dir():
        raise FileNotFoundError("Provided private 1280D embedding directory does not exist")
    with closing(ev.open_database(db)) as conn:
        cohorts = {head: ev._catalog(conn, head, experimental=True) for head in ev.MODELS}
        if {meta["preprocessing_version"] for meta in cohorts.values()} != {V5_PREPROCESSING}:
            raise ValueError("Genre/Mood dominant cohorts do not both use corrected experimental Rust v5")
        sample = ev.load_sample(conn, cohorts, limit, seed)
        counters = {
            "sampled_paired_head_vectors": sample["sample_size"],
            "compatible_head_pairs": 0,
            "head_provenance_mismatches": 0,
            "embedding_valid": 0,
            "embedding_missing": 0,
            "embedding_invalid_or_incompatible": 0,
        }
        fingerprint = None
        for key in sample["tracks"]:
            matching = provenance(conn, key, cohorts)
            if matching is None:
                counters["head_provenance_mismatches"] += 1
                continue
            counters["compatible_head_pairs"] += 1
            if embedding_dir is None:
                continue
            path = embedding_dir / filename_for_key(key)
            if not path.is_file():
                counters["embedding_missing"] += 1
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Embedding JSON is not an object")
                audio, patches, encoder = matching
                validate_embedding(
                    data, key, audio, patches, encoder, V5_PREPROCESSING, fingerprint
                )
            except (ValueError, KeyError, TypeError, OSError, UnicodeError):
                counters["embedding_invalid_or_incompatible"] += 1
            else:
                fingerprint = data["representation_fingerprint"]
                counters["embedding_valid"] += 1
        # The report includes no song file names, artist/title IDs, audio hashes,
        # human ratings, vectors, per-track errors or local network paths.
        return {
            "schema": "lyrion-local-feature-readiness-aggregate-v1",
            "phase": "2_L0_read_only_inventory",
            "status": "experimental_research_only_not_production_validated",
            "database_schema_version": 3,
            "sampling": {"method": "existing_pair_cohort_reservoir", "seed": seed,
                         "max_songs": limit,
                         "compatible_87d_56d_total_before_sample": sample["valid_total"],
                         "invalid_joined_head_vectors_excluded": sample["invalid"]},
            "head_cohorts": {
                head: {"dimension": meta["dimensions"],
                       "model_aggregation": ev.AGGREGATION,
                       "preprocessing": meta["preprocessing_version"],
                       "validated_against_essentia": meta["validated"],
                       "dominant_cohort_rows": meta["track_count"]}
                for head, meta in cohorts.items()
            },
            "counts": {
                **{k: v for k, v in counters.items()
                   if k not in ("embedding_valid", "embedding_missing",
                                "embedding_invalid_or_incompatible")},
                "embedding_status": "not_assessed_no_directory" if embedding_dir is None
                                     else "verified_against_same_head_audio",
                "embedding_valid": None if embedding_dir is None else counters["embedding_valid"],
                "embedding_missing": None if embedding_dir is None else counters["embedding_missing"],
                "embedding_invalid_or_incompatible": (
                    None if embedding_dir is None else counters["embedding_invalid_or_incompatible"]
                ),
            },
            "guarantees": {"feature_sqlite_opened_read_only": True,
                           "no_audio_or_onnx_inference": True,
                           "no_music_identity_or_song_vectors_output": True,
                           "does_not_claim_cpp_parity_or_product_readiness": True},
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True,
                   help="Existing schema-v3 feature DB; NEVER modified or created")
    p.add_argument("--embedding-dir", type=Path,
                   help="Optional private 1280D song sidecars; no directory means NOT ASSESSED")
    p.add_argument("--limit", type=int, default=100,
                   help="Maximum same-song head pairs to inspect (1..300; default 100)")
    p.add_argument("--seed", type=int, default=20261021)
    p.add_argument("--out", type=Path,
                   help="Optional NEW JSON path; refuses to overwrite; stdout otherwise")
    args = p.parse_args()
    try:
        if args.out is not None and args.out.exists():
            raise FileExistsError("Aggregate report already exists; choose a new filename")
        result = report(args.db, args.embedding_dir, limit=args.limit, seed=args.seed)
        blob = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.out is not None:
            with args.out.open("x", encoding="utf-8") as file:
                file.write(blob)
        else:
            print(blob, end="")
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        # Errors are intentionally brief. Do not print private track IDs.
        p.exit(2, f"Local feature readiness audit failed: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
