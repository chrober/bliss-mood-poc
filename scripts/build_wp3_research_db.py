#!/usr/bin/env python3
"""Build a PRIVATE, self-contained WP3 Bliss23 + Essentia87/56 research SQLite.

Reads the two existing original feature sources in SQLite mode=ro/query_only,
uses exact binary track keys, strict source/model provenance, and optionally
joins genuine Lyrion artist/album/recording identities. Never scans audio,
invents metadata, changes source databases, or overwrites an existing target.

The private output contains track identities and vectors; NEVER commit/share it.
Only a non-identifying aggregate is printed on stdout.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import struct
import sys

from audit_bliss_essentia_join import (
    BLISS_COLUMNS, open_bliss, bliss_vector, compatible_essentia_provenance,
)
import evaluate_similarity as ev

SCHEMA = "lyrion-wp3-research-snapshot-v1"
MIN_LIMIT = 1
MAX_LIMIT = 300
FIELDS = ("artist_group", "album_group", "recording_group")


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def select_sources(bliss_path: Path, feature_path: Path, *, limit: int,
                   seed: int) -> tuple[list[dict], dict]:
    if type(limit) is not int or not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError("Sample size must be between 1 and 300")
    if type(seed) is not int:
        raise ValueError("Seed must be an integer")
    rows = []
    counts = {
        "eligible_feature_head_pairs": 0,
        "invalid_feature_vectors_excluded": 0,
        "selected_feature_head_pairs": 0,
        "rejected_feature_provenance": 0,
        "missing_ambiguous_invalid_bliss": 0,
        "paired_bliss_essentia_tracks": 0,
    }
    with closing(open_bliss(bliss_path)) as bliss:
        with closing(ev.open_database(feature_path)) as features:
            cohorts = {head: ev._catalog(features, head, experimental=True)
                       for head in ("genre", "moodtheme")}
            if len({c["preprocessing_version"] for c in cohorts.values()}) != 1:
                raise ValueError("Classifier model heads have incompatible preprocessing")
            selection = ev.load_sample(features, cohorts, limit, seed)
            counts["eligible_feature_head_pairs"] = selection["valid_total"]
            counts["invalid_feature_vectors_excluded"] = selection["invalid"]
            counts["selected_feature_head_pairs"] = selection["sample_size"]
            for key, vectors in selection["tracks"].items():
                if not isinstance(key, str) or not key or "\x00" in key:
                    counts["rejected_feature_provenance"] += 1
                    continue
                provenance = compatible_essentia_provenance(features, key, cohorts)
                if provenance is None:
                    counts["rejected_feature_provenance"] += 1
                    continue
                state, bliss_vector_values = bliss_vector(bliss, key)
                if state != "valid":
                    counts["missing_ambiguous_invalid_bliss"] += 1
                    continue
                audio_sha, patches, encoder_sha = provenance
                rows.append({
                    "key": key,
                    "bliss": struct.pack("<23d", *bliss_vector_values),
                    "genre": struct.pack("<87f", *vectors["genre"]),
                    "moodtheme": struct.pack("<56f", *vectors["moodtheme"]),
                    "audio_sha": audio_sha,
                    "patches": patches,
                    "encoder_sha": encoder_sha,
                })
            counts["paired_bliss_essentia_tracks"] = len(rows)
            meta = {
                "sample_limit": limit, "sample_seed": seed,
                "chosen_head_model_ids": {
                    head: {
                        "model_key": cohort["model_key"],
                        "preprocessing": cohort["preprocessing_version"],
                        "validated_against_essentia": cohort["validated"],
                        "class_labels": cohort["labels"],
                    } for head, cohort in cohorts.items()
                },
            }
    return rows, {"counts": counts, "models": meta}


def group_enrichment(bliss_path: Path, feature_path: Path, *,
                     snapshot: Path | None, library: Path | None,
                     limit: int, seed: int, keys: set[str]) -> tuple[dict, dict]:
    if (snapshot is None) != (library is None):
        raise ValueError("Lyrion snapshot and library sources must be supplied together")
    if snapshot is None:
        return {}, {"status": "NOT_AVAILABLE", "blocking_reason_code": "LYRION_GROUP_SOURCES_NOT_PROVIDED",
                    "validated_artist_album_recording_holdout": False,
                    "verified_grouped_songs": 0}
    from derive_lyrion_research_groups import generate_private_groups
    groups, report = generate_private_groups(
        bliss_path, feature_path, snapshot, library, limit=limit,
        seed=seed, preflight=True,
    )
    if not report["ready_for_grouped_study"]:
        return {}, {
            "status": "BLOCKED",
            "blocking_reason_code": report["blocking_reason_code"],
            "validated_artist_album_recording_holdout": False,
            "verified_grouped_songs": 0,
            "source_grouping_counts": report["counts"],
        }
    if set(groups) != keys:
        # Do not publish an apparently grouped training set with missing keys.
        return {}, {
            "status": "BLOCKED",
            "blocking_reason_code": "GROUP_COHORT_DOES_NOT_MATCH_PAIRED_DATA",
            "validated_artist_album_recording_holdout": False,
            "verified_grouped_songs": 0,
        }
    return groups, {
        "status": "READY",
        "blocking_reason_code": None,
        "validated_artist_album_recording_holdout": True,
        "verified_grouped_songs": len(groups),
        "source_grouping_counts": report["counts"],
        "connected_groups": report["artist_album_recording_connected_components"],
        "train_songs": report["train_songs"],
        "holdout_songs": report["holdout_songs"],
        # The snapshot shape and selected LMS URLMD5 match are verified;
        # current LMS scan/root freshness is NOT independently certified.
        "live_lms_snapshot_freshness_certified": False,
    }


def build(bliss_path: Path, feature_path: Path, output: Path | None, *,
          snapshot: Path | None = None, library: Path | None = None,
          limit: int = 300, seed: int = 20261029) -> dict:
    if not bliss_path.is_file() or not feature_path.is_file():
        raise ValueError("The two existing feature source databases are required")
    if (snapshot is None) != (library is None):
        raise ValueError("Lyrion snapshot and library sources must be supplied together")
    paths = [bliss_path, feature_path] + ([snapshot, library] if snapshot is not None else [])
    if any(not p.is_file() for p in paths):
        raise ValueError("Required read-only metadata source does not exist")
    if len({str(p.resolve()).casefold() for p in paths}) != len(paths):
        raise ValueError("Different source roles must use distinct input files")
    if output is not None and (output.exists() or output.is_symlink()):
        raise FileExistsError("Research database already exists; refusing overwrite")
    if output is not None and str(output.resolve()).casefold() in {
            str(p.resolve()).casefold() for p in paths}:
        raise ValueError("Refuse to use source database as output")

    before = {str(p.resolve()): digest(p) for p in paths}
    rows, selected = select_sources(bliss_path, feature_path, limit=limit, seed=seed)
    if not rows:
        raise ValueError("No exact-key paired Bliss/Essentia tracks in selected cohort")
    groups, group_report = group_enrichment(
        bliss_path, feature_path, snapshot=snapshot, library=library,
        limit=limit, seed=seed, keys={r["key"] for r in rows},
    )
    after = {str(p.resolve()): digest(p) for p in paths}
    if before != after:
        raise ValueError("A source changed while building the immutable research cohort")

    status = "READY_FOR_GROUPED_RESEARCH" if group_report["status"] == "READY" else "FEATURE_SNAPSHOT_ONLY_GROUPS_UNVERIFIED"
    report = {
        "schema": SCHEMA,
        "status": status,
        "counts": selected["counts"],
        "groups": group_report,
        "source_databases_unchanged": True,
        "source_bliss_essentia_audio_byte_identity_independently_certified": False,
        "teacher_pretraining_overlap_ruled_out": False,
        "general_similarity_quality_evaluated": False,
        "private_song_keys_vectors_written_to_local_sqlite": output is not None,
    }
    if output is None:
        return report

    # Exclusive create at the final destination; never silently replace an
    # existing DB. Inputs have already passed all read-only validations.
    fd = os.open(str(output), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(output)) as conn:
            conn.execute("PRAGMA user_version=1")
            with conn:
                conn.executescript("""
                    CREATE TABLE metadata (
                        key TEXT PRIMARY KEY, value TEXT NOT NULL
                    );
                    CREATE TABLE paired_tracks (
                        track_key TEXT PRIMARY KEY COLLATE BINARY,
                        bliss_f64_le BLOB NOT NULL,
                        genre_f32_le BLOB NOT NULL,
                        moodtheme_f32_le BLOB NOT NULL,
                        audio_sha256 TEXT NOT NULL,
                        patches_analyzed INTEGER NOT NULL CHECK(patches_analyzed > 0),
                        encoder_sha256 TEXT NOT NULL,
                        artist_group TEXT,
                        album_group TEXT,
                        recording_group TEXT
                    );
                """)
                values = [
                    ("schema", SCHEMA),
                    ("selection_json", json.dumps(selected["models"], sort_keys=True)),
                    ("source_sha256_json", json.dumps(before, sort_keys=True)),
                    ("group_readiness", group_report["status"]),
                    ("group_blocker", group_report.get("blocking_reason_code") or ""),
                    ("source_join_claim", "exact_file_key_only_no_independent_audio_byte_verification"),
                ]
                # Source file paths appear only INSIDE this private local DB.
                conn.executemany("INSERT INTO metadata VALUES (?,?)", values)
                conn.executemany("""
                    INSERT INTO paired_tracks VALUES (?,?,?,?,?,?,?,?,?,?)
                """, [(
                    r["key"], r["bliss"], r["genre"], r["moodtheme"],
                    r["audio_sha"], r["patches"], r["encoder_sha"],
                    *(groups.get(r["key"], {}).get(field) for field in FIELDS),
                ) for r in rows])
    except BaseException:
        # Only this invocation's just-created output may be removed.
        # Never delete pre-existing research files or any source.
        if output.is_file():
            output.unlink()
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bliss-db", type=Path, required=True)
    parser.add_argument("--feature-db", type=Path, required=True)
    parser.add_argument("--repeat-identity-db", type=Path)
    parser.add_argument("--lyrion-library-db", type=Path)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--out-db", type=Path,
                        help="Create NEW private SQLite research DB (omit for no-write preflight)")
    args = parser.parse_args()
    try:
        summary = build(
            args.bliss_db, args.feature_db, args.out_db,
            snapshot=args.repeat_identity_db, library=args.lyrion_library_db,
            limit=args.limit, seed=args.seed,
        )
        print(json.dumps(summary, indent=2, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error, RuntimeError):
        parser.exit(2, "WP3 research DB build blocked: source schema, identity, file state or permissions invalid; no original data modified\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
