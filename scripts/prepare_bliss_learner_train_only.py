#!/usr/bin/env python3
"""WP2-P2: isolate the EXISTING Rust bliss-learner on TRAIN triplets only.

Input = private survey triplets, explicit private artist/album/recording groups,
read-only existing Bliss SQLite. Output = a NEW private minimal SQLite with
only training songs, train-only JSON triplets and hash-bound manifest.
No learner execution or audio processing. Never uploads or prints track keys.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

from audit_bliss_essentia_join import BLISS_COLUMNS, open_bliss, bliss_vector
from research_grouped_split import grouped_triplet_partition


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_new(path: Path, value: object) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(payload)


def prepare(
    bliss_db: Path, triplets: list, metadata: dict, output_dir: Path,
    *, seed: int = 20261029, test_fraction: float = 0.25,
) -> dict:
    if not bliss_db.is_file():
        raise ValueError("Existing Bliss database required")
    if not isinstance(metadata, dict):
        raise ValueError("Private group metadata must be an object")
    # Do ALL checks before creating output. A failed partition must
    # never produce a lookalike trained-on-all triplet source.
    split = grouped_triplet_partition(
        triplets, metadata, test_fraction=test_fraction, seed=seed
    )
    train_indices = split["train_triplet_indices"]
    held_indices = split["holdout_triplet_indices"]
    if len(train_indices) < 5:
        raise ValueError("Existing bliss-learner requires at least 5 training triplets")
    train_triplets = [list(triplets[i]) for i in train_indices]
    train_songs = {key for t in train_triplets for key in t}
    held_songs = {key for i in held_indices for key in triplets[i]}
    if train_songs & held_songs:
        raise ValueError("Training input overlaps heldout songs")
    # Only source from exact 23D columns. Do not import holdout features.
    source_stamp = (bliss_db.stat().st_size, bliss_db.stat().st_mtime_ns)
    rows = []
    with closing(open_bliss(bliss_db)) as source:
        for key in sorted(train_songs):
            status, feature = bliss_vector(source, key)
            if status != "valid":
                raise ValueError("A training track lacks unique finite Bliss 23D data")
            rows.append((key, *feature))
    if (bliss_db.stat().st_size, bliss_db.stat().st_mtime_ns) != source_stamp:
        raise ValueError("Source Bliss database changed during read")
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing private research output")
    output_dir.mkdir(parents=False, mode=0o700, exist_ok=False)
    db_path = output_dir/"train-only-bliss.db"
    triplet_path = output_dir/"train-only-triplets.json"
    manifest_path = output_dir/"train-only-manifest-private.json"
    # Always materialize new, isolated research-only SQLite; the unchanged
    # Rust binary can use its normal open() without access to the source DB.
    columns = ", ".join('"' + name + '" REAL NOT NULL' for name in BLISS_COLUMNS)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(f'CREATE TABLE TracksV2 ("File" TEXT PRIMARY KEY COLLATE BINARY, {columns})')
        conn.executemany(
            f'INSERT INTO TracksV2 VALUES ({",".join(["?"]*24)})', rows
        )
        conn.commit()
    _write_new(triplet_path, train_triplets)
    manifest = {
        "schema": "lyrion_train_only_legacy_bliss_learner_bundle_private_v1",
        "status": "NOT_TRAINED__TRAIN_ONLY_STAGING",
        "seed": seed,
        "test_fraction_requested": test_fraction,
        "train_triplet_count": len(train_triplets),
        "heldout_triplet_count": len(held_indices),
        "training_track_count": len(train_songs),
        "connected_group_components": split["group_component_count"],
        "bliss_feature_columns_order": list(BLISS_COLUMNS),
        "input_audio_or_onnx_invoked": False,
        "raw_source_db_not_written": True,
        "source_db_stat_size_and_mtime_only": list(source_stamp),
        "train_triplets_sha256": _sha256(triplet_path),
        "train_only_db_sha256": _sha256(db_path),
        # Private manifest: hashes are not anonymous with low-entropy song
        # names. The entire output bundle must stay private.
        "train_track_keys_sha256": hashlib.sha256(
            json.dumps(sorted(train_songs),ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "heldout_track_keys_sha256": hashlib.sha256(
            json.dumps(sorted(held_songs),ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "train_only_rust_learner_invocation": {
            "argument_names": ["--db", "--triplets", "--output"],
            "notifications": "disabled",
            "production_source_database_must_not_be_passed": True,
        },
        "upstream_learner_internal_random_cv_remains_not_grouped": True,
        "upstream_learner_final_matrix_trained_only_on_staged_train_subset": True,
        "independent_model_gain_not_measured_here": True,
    }
    _write_new(manifest_path, manifest)
    return {
        "schema": "lyrion_train_only_legacy_bliss_learner_aggregate_v1",
        "status": "PRIVATE_STAGING_CREATED__NO_TRAINING_EXECUTED",
        "train_triplets": len(train_indices),
        "holdout_triplets": len(held_indices),
        "train_tracks": len(train_songs),
        "heldout_tracks": len(held_songs),
        "connected_components": split["group_component_count"],
        "train_holdout_song_overlap": 0,
        "bliss_original_source_unchanged": True,
        "only_training_records_written_to_private_staging": True,
        "no_model_trained": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bliss-db", type=Path, required=True)
    parser.add_argument("--triplets-json", type=Path, required=True)
    parser.add_argument("--group-metadata-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory, never an existing output")
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args()
    try:
        trips = json.loads(args.triplets_json.read_text(encoding="utf-8"))
        groups = json.loads(args.group_metadata_json.read_text(encoding="utf-8"))
        report = prepare(args.bliss_db, trips, groups, args.output_dir,seed=args.seed)
        print(json.dumps(report, ensure_ascii=True, indent=2))
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError):
        # Never reveal private track/file identifiers from data exceptions.
        parser.exit(2, "Private train-only staging failed; inputs or partition incompatible\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
