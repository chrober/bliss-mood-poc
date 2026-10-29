#!/usr/bin/env python3
"""Research WP3-R0: read-only exact-key Bliss 23D <-> Essentia 87/56D QC.

Only aggregated, nonidentifying diagnostics are returned. Does not infer that
matching file keys prove identical audio bytes. Experimental model predictions
are NOT genre/mood ground truth or a production validation. No audio decoding.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import random
import re
import sqlite3
import sys

import evaluate_similarity as ev

# Source contract: chrober/bliss-learner src/main.rs FEATURE_COLUMNS (main, 2026-10-29).
BLISS_COLUMNS = (
    "Tempo", "Zcr",
    "MeanSpectralCentroid", "StdDevSpectralCentroid",
    "MeanSpectralRolloff", "StdDevSpectralRolloff",
    "MeanSpectralFlatness", "StdDevSpectralFlatness",
    "MeanLoudness", "StdDevLoudness",
    "Chroma1", "Chroma2", "Chroma3", "Chroma4", "Chroma5",
    "Chroma6", "Chroma7", "Chroma8", "Chroma9", "Chroma10",
    "Chroma11", "Chroma12", "Chroma13",
)
assert len(BLISS_COLUMNS) == len(set(BLISS_COLUMNS)) == 23

SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_SAMPLE = 300


def open_bliss(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("Bliss DB is missing")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        # Ensure the real 23-value contract, do not silently select an alias.
        columns = conn.execute("PRAGMA table_info(TracksV2)").fetchall()
        by_name = {col[1].casefold(): col[1] for col in columns}
        required = ("File", *BLISS_COLUMNS)
        if any(by_name.get(name.casefold()) != name for name in required):
            raise ValueError("Bliss TracksV2 lacks the exact learner 23D column contract")
        if len(by_name) != len(columns):
            raise ValueError("Ambiguous Bliss column names")
        return conn
    except BaseException:
        conn.close()
        raise


def bliss_vector(conn: sqlite3.Connection, key: str) -> tuple[str, tuple[float, ...] | None]:
    """Never fuzzy-match artist/title/file suffix or silently pick duplicate File."""
    if not isinstance(key, str) or not key or "\0" in key:
        return "invalid_key", None
    names = ", ".join('"' + name + '"' for name in BLISS_COLUMNS)
    rows = conn.execute(
        f'SELECT {names} FROM TracksV2 WHERE File = ? COLLATE BINARY LIMIT 2', (key,)
    ).fetchall()
    if not rows:
        return "missing", None
    if len(rows) != 1:
        return "ambiguous", None
    values = rows[0]
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in values):
        return "invalid", None
    return "valid", tuple(float(x) for x in values)


def compatible_essentia_provenance(
    conn: sqlite3.Connection, key: str, cohorts: dict,
) -> tuple[str, int, str] | None:
    """Require both frozen selected heads, one source hash and one encoder hash."""
    rows = conn.execute(
        """SELECT t.model_id, t.model_key, t.audio_sha256,
                  t.patches_analyzed, m.embedding_model, m.classification_model,
                  m.models_sha256_json, m.preprocessing_version, m.aggregation
           FROM feature_tracks t
           JOIN feature_models m ON t.model_key=m.model_key
           WHERE t.track_file=? COLLATE BINARY
             AND t.model_id IN ('genre','moodtheme')""", (key,)
    ).fetchall()
    if len(rows) != 2 or {x[0] for x in rows} != {"genre", "moodtheme"}:
        return None
    audios, patches, encoders, encoder_names, preprocessings = (
        set(), set(), set(), set(), set()
    )
    for head, model_key, audio, patches_analyzed, encoder, classifier, sha_json, prep, agg in rows:
        if (model_key != cohorts[head]["model_key"]
                or agg != ev.AGGREGATION or prep != cohorts[head]["preprocessing_version"]
                or not isinstance(audio, str) or not SHA256.fullmatch(audio)
                or type(patches_analyzed) is not int or patches_analyzed <= 0
                or not isinstance(encoder, str) or not encoder
                or not isinstance(classifier, str) or not classifier):
            return None
        try:
            hashes = json.loads(sha_json)
        except (ValueError, TypeError):
            return None
        if not isinstance(hashes, dict) or any(
                not isinstance(hashes.get(name), str) or
                not SHA256.fullmatch(hashes[name]) for name in (encoder, classifier)):
            return None
        audios.add(audio.lower())
        patches.add(patches_analyzed)
        encoders.add(hashes[encoder].lower())
        encoder_names.add(encoder)
        preprocessings.add(prep)
    if any(len(s) != 1 for s in (
        audios, patches, encoders, encoder_names, preprocessings
    )):
        return None
    return next(iter(audios)), next(iter(patches)), next(iter(encoders))


def report(bliss_db: Path, feature_db: Path, *, limit: int = 100,
           seed: int = 20261029) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_SAMPLE:
        raise ValueError("Sample limit must be 1..300")
    if type(seed) is not int:
        raise ValueError("Sampling seed must be an integer")
    with closing(open_bliss(bliss_db)) as bliss:
        with closing(ev.open_database(feature_db)) as essentia:
            cohorts = {
                name: ev._catalog(essentia, name, experimental=True)
                for name in ("genre", "moodtheme")
            }
            if len({v["preprocessing_version"] for v in cohorts.values()}) != 1:
                raise ValueError("Mixed Essentia head preprocessing versions")
            sample = ev.load_sample(essentia, cohorts, limit, seed)
            counts = {
                "essentia_head_pairs_selected": sample["sample_size"],
                "essentia_head_pairs_eligible_total": sample["valid_total"],
                "essentia_head_pairs_invalid_excluded": sample["invalid"],
                "essentia_head_provenance_rejected_in_sample": 0,
                "bliss_exact_key_missing": 0,
                "bliss_duplicate_exact_key": 0,
                "bliss_invalid_23d": 0,
                "bliss_23d_valid_and_paired": 0,
            }
            # Research-only in-memory vector sample; never returned or written.
            # A real PCA/CCA/PLS stage must use a separately approved private,
            # group-labelled train/test dataset; this stage proves coverage only.
            for key in sample["tracks"]:
                if compatible_essentia_provenance(essentia, key, cohorts) is None:
                    counts["essentia_head_provenance_rejected_in_sample"] += 1
                    continue
                status, _bliss_values = bliss_vector(bliss, key)
                if status == "missing":
                    counts["bliss_exact_key_missing"] += 1
                elif status == "ambiguous":
                    counts["bliss_duplicate_exact_key"] += 1
                elif status == "valid":
                    counts["bliss_23d_valid_and_paired"] += 1
                else:
                    counts["bliss_invalid_23d"] += 1
            assert (
                counts["essentia_head_provenance_rejected_in_sample"]
                + counts["bliss_exact_key_missing"]
                + counts["bliss_duplicate_exact_key"]
                + counts["bliss_invalid_23d"]
                + counts["bliss_23d_valid_and_paired"]
                == sample["sample_size"]
            )
            return {
                "schema": "bliss_essentia_exact_key_join_aggregate_v1",
                "status": "RESEARCH_READ_ONLY_COVERAGE_NOT_MUSICAL_VALIDATION",
                "bliss_feature_dimensions": len(BLISS_COLUMNS),
                "essentia_head_dimensions": {"genre": 87, "moodtheme": 56},
                "embedding_1280d": "NOT_ASSESSED_SEPARATE_SIDECARS_REQUIRED",
                "sampling": {
                    "source": "selected_dominant_essentia_87d_56d_cohort",
                    "method": "deterministic_reservoir_across_exact_sorted_head_keys",
                    "seed": seed,
                    "max_songs": limit,
                },
                "model_validated_against_essentia": {
                    name: data["validated"] for name, data in cohorts.items()
                },
                "counts": counts,
                "guarantees": {
                    "sqlite_read_only_query_only": True,
                    "no_audio_or_onnx_or_worker_invocation": True,
                    "no_private_tracks_or_vectors_or_hashes_in_report": True,
                    "track_identity": "exact_binary_TracksV2.File_equals_feature_tracks.track_file",
                    "matching_keys_do_not_prove_audio_byte_identity": True,
                    "no_artist_album_split_validated": True,
                    "no_predictive_or_similarity_quality_claim": True,
                },
            }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bliss-db", type=Path, required=True)
    p.add_argument("--feature-db", type=Path, required=True)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--seed", type=int, default=20261029)
    p.add_argument("--out", type=Path,
                   help="New aggregate JSON path; never overwrites a previous report")
    args = p.parse_args()
    try:
        if args.out is not None and args.out.exists():
            raise FileExistsError("Refuse existing report")
        outcome = report(args.bliss_db, args.feature_db,
                         limit=args.limit, seed=args.seed)
        payload = json.dumps(outcome, indent=2, allow_nan=False) + "\n"
        if args.out is None:
            print(payload, end="")
        else:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(payload)
    except (OSError, ValueError, sqlite3.Error):
        # Never echo a private full DB path, SQL row or track identity.
        p.exit(2, "Bliss/Essentia audit failed: incompatible or unavailable read-only inputs\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
