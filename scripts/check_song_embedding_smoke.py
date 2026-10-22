#!/usr/bin/env python3
"""Fail-closed CI parity oracle for research-only pooled 1280D embeddings.

Never publish source audio, raw classifier scores or embedding vectors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import sqlite3


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_process_embedding_outputs(directory: Path, *, required: bool = False) -> list[Path]:
    """Match only embedding outputs, not similarly prefixed classification reports.

    The research parity gate expects four exactly numbered, independent workers.
    A standalone one-song smoke has no such files and may omit the gate;
    the multiworker workflow passes --require-process-workers to fail closed.
    """
    pattern = re.compile(r"process-worker-([1-9][0-9]*)[.]json")
    indexed = {
        int(match.group(1)): path
        for path in directory.glob("process-worker-*.json")
        if (match := pattern.fullmatch(path.name)) is not None
    }
    if not indexed and not required:
        return []
    expected = set(range(1, 5))
    if set(indexed) != expected:
        raise AssertionError(
            f"Expected embedding outputs from workers 1..4; got {sorted(indexed)}"
        )
    return [indexed[index] for index in sorted(expected)]


def check(directory: Path, *, require_process_workers: bool = False) -> dict:
    off = read(directory / "off.json")
    on = read(directory / "on.json")
    threaded = read(directory / "threads2.json")
    emb = read(directory / "embedding.json")
    emb_threaded = read(directory / "embedding-threads2.json")
    raw = read(directory / "patch-dump.json")

    # Exact original classifier output, not merely an average-score tolerance.
    assert off["classifications"] == on["classifications"], "Export changed classifier results"
    assert off["schema_version"] == on["schema_version"] == 3
    assert off["preprocessing_version"] == on["preprocessing_version"]
    assert off["patches_analyzed"] == on["patches_analyzed"]
    assert len(off["classifications"]) == 2
    assert set(off["classifications"]) == {"genre", "moodtheme"}
    assert on["audio_sha256"] == emb["audio_sha256"] == raw["audio_sha256"]

    assert emb["schema_version"] == 1
    assert emb["kind"] == "discogs_effnet_song_embedding"
    assert emb["validation_status"] == "experimental_unvalidated"
    assert emb["dimension"] == 1280
    assert emb["encoder_model"] == raw["embedding_model"]
    assert emb["encoder_sha256"] == raw["embedding_model_sha256"]
    assert emb["preprocessing_version"] == on["preprocessing_version"]
    assert emb["pooling_version"] == "patch_f64_arithmetic_mean_v1"
    assert emb["normalization_version"] == "song_f64_l2_then_cast_f32_v1"
    assert emb["track_file"] == "smoke.wav"
    assert "track_file" not in emb_threaded
    assert emb["patches_analyzed"] == len(raw["embeddings"]) == on["patches_analyzed"]
    assert emb["patches_analyzed"] > 0

    fingerprint_contract = [
        1, emb["encoder_model"], emb["encoder_sha256"], emb["preprocessing_version"],
        emb["pooling_version"], emb["normalization_version"], emb["dimension"],
    ]
    fingerprint = hashlib.sha256(json.dumps(
        fingerprint_contract, separators=(",", ":"), ensure_ascii=False
    ).encode()).hexdigest()
    assert emb["representation_fingerprint"] == fingerprint
    assert emb_threaded["representation_fingerprint"] == fingerprint

    sums = [0.] * 1280
    for patch in raw["embeddings"]:
        assert len(patch) == 1280
        for i, value in enumerate(patch):
            assert math.isfinite(value)
            sums[i] += value
    means = [v / len(raw["embeddings"]) for v in sums]
    magnitude = math.sqrt(sum(v * v for v in means))
    assert magnitude > 0 and math.isfinite(magnitude)
    expected = [v / magnitude for v in means]
    actual = emb["vector_f32"]
    actual_threaded = emb_threaded["vector_f32"]
    assert len(actual) == len(actual_threaded) == 1280
    assert all(math.isfinite(v) for v in actual)
    norm = math.sqrt(sum(v * v for v in actual))
    assert abs(norm - 1.0) < 1e-5
    diff = max(abs(a - b) for a, b in zip(expected, actual))
    assert diff < 1e-5, f"Embedding vs independently pooled raw patches: {diff}"
    thread_diff = max(abs(a - b) for a, b in zip(actual, actual_threaded))
    assert thread_diff < 1e-5, f"ONNX thread nondeterminism exceeded tolerance: {thread_diff}"

    # Four independently initialized ONNX worker processes on the SAME audio.
    # Different completion order cannot alter immutable song embeddings.
    workers = discover_process_embedding_outputs(
        directory, required=require_process_workers
    )
    if workers:
        for worker in workers:
            output = read(worker)
            if output["vector_f32"] != actual:
                raise AssertionError("Process-worker result differs from single-process embedding")
            if output["representation_fingerprint"] != emb["representation_fingerprint"]:
                raise AssertionError("Process-worker model/pooling fingerprint differs")
            if output["audio_sha256"] != emb["audio_sha256"]:
                raise AssertionError("Process-worker audio provenance differs")

    for head in off["classifications"]:
        ref = off["classifications"][head]["scores"]
        check_scores = threaded["classifications"][head]["scores"]
        assert ref.keys() == check_scores.keys()
        assert max(abs(ref[k] - check_scores[k]) for k in ref) < 1e-5

    # Schema v3 remains identical and does not contain latent embedding rows.
    def get_db_rows(name):
        with sqlite3.connect(directory / name) as db:
            assert db.execute("PRAGMA user_version").fetchone()[0] == 3
            names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert not any("embedding" in name for name in names)
            models = db.execute("SELECT * FROM feature_models ORDER BY model_key").fetchall()
            tracks = db.execute(
                "SELECT track_file, model_id, capability, audio_sha256, model_key, scores_f32_le, patches_analyzed "
                "FROM feature_tracks ORDER BY track_file, model_id"
            ).fetchall()
            assert len(tracks) == len(models) == 2
            return models, tracks
    assert get_db_rows("off.db") == get_db_rows("on.db"), "SQLite genre/mood regression"

    return {
        "status": "PASS",
        "source": "synthetic deterministic 6-second PCM",
        "pinned_rust_v5_revision": "2c3d44401436b3b41b6e067199016a1ed2335fbf",
        "patches": emb["patches_analyzed"],
        "embedding_dimension": len(actual),
        "embedding_unit_norm_error": abs(norm - 1.0),
        "max_pooled_patch_reference_error": diff,
        "max_1_vs_2_threads_embedding_error": thread_diff,
        "independent_process_workers_identical": len(workers) if workers else "NOT_TESTED",
        "classification_equal_without_export": True,
        "sqlite_schema_v3_and_head_rows_identical": True,
        "official_tf_embedding_parity": "NOT_TESTED_IN_THIS_WORKFLOW",
        "real_audio_similarity_benchmark": "NOT_YET_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--require-process-workers", action="store_true",
                   help="Require four numbered embedding outputs from isolated workers")
    p.add_argument("--summary", type=Path, required=True)
    args = p.parse_args()
    summary = check(args.directory, require_process_workers=args.require_process_workers)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    print("PASS: independent pooled-patch oracle, exact heads, v3 DB and thread checks")


if __name__ == "__main__":
    main()
