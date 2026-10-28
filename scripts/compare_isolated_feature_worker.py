#!/usr/bin/env python3
"""Compare actual direct and isolated FeatureEngine inference on user-supplied audio.

No audio is copied and no SQLite/embeddings are written. Reports remain in memory.
Only prints a summary or the first mismatch, never raw classifier scores.
Requires the same compiled bliss-mood binary and locally installed model files.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import sys


def f32_bits(value: float) -> bytes:
    return struct.pack("<f", float(value))


def compare_reports(direct: dict, isolated: dict) -> tuple[int, int]:
    """Check all source/model identities and exact f32 classifier score bits.

    Timing is intentionally excluded because running in another process
    changes session startup and wall-clock timings by design.
    """
    keys = (
        "schema_version", "preprocessing_version", "aggregation",
        "audio_sha256", "sample_rate", "patches_analyzed", "threads",
    )
    for key in keys:
        if direct.get(key) != isolated.get(key):
            raise ValueError(f"Report identity mismatch: {key}")
    direct_heads = direct["classifications"]
    isolated_heads = isolated["classifications"]
    if direct_heads.keys() != isolated_heads.keys():
        raise ValueError("Selected classification-head IDs differ")
    total_labels = 0
    for model in sorted(direct_heads):
        left, right = direct_heads[model], isolated_heads[model]
        for field in (
            "capability", "output_type", "aggregation", "embedding_model",
            "classification_model", "models_sha256", "model_key",
            "validated_against_essentia",
        ):
            if left.get(field) != right.get(field):
                raise ValueError(f"{model}: model identity mismatch: {field}")
        labels = left["scores"]
        if labels.keys() != right["scores"].keys():
            raise ValueError(f"{model}: classification labels differ")
        for label in labels:
            try:
                l, r = float(labels[label]), float(right["scores"][label])
                if not math.isfinite(l) or not math.isfinite(r):
                    raise ValueError(f"{model}: non-finite classification: {label}")
                if f32_bits(l) != f32_bits(r):
                    raise ValueError(f"{model}: f32 score mismatch: {label}")
            except (TypeError, OverflowError, struct.error) as exc:
                raise ValueError(f"{model}: invalid classification score: {label}") from exc
            total_labels += 1
    return len(direct_heads), total_labels


def run_analysis(arguments: list[str]) -> dict:
    completed = subprocess.run(
        arguments, capture_output=True, text=True, encoding="utf-8",
        check=False, timeout=7200,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{arguments[1]} exited {completed.returncode}; "
            "see stderr on your local host (not persisted by this script)"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{arguments[1]} produced invalid JSON") from exc


def validate_embedding(embedding: dict | None, report: dict) -> None:
    if not isinstance(embedding, dict):
        raise ValueError("Missing isolated song embedding")
    values = embedding.get("vector_f32")
    if not isinstance(values, list) or len(values) != 1280:
        raise ValueError("Missing 1280D embedding vector")
    if embedding.get("dimension") != 1280:
        raise ValueError("Unexpected embedding dimensions")
    if embedding.get("audio_sha256") != report["audio_sha256"]:
        raise ValueError("Song embedding audio hash differs from report")
    if embedding.get("patches_analyzed") != report["patches_analyzed"]:
        raise ValueError("Song embedding patch count differs from report")
    if not all(isinstance(x, (float, int)) and math.isfinite(x) for x in values):
        raise ValueError("Non-finite isolated embedding")
    norm = math.sqrt(sum(float(x) ** 2 for x in values))
    if abs(norm - 1.0) > 1e-5:
        raise ValueError("Isolated embedding is not normalized")


def compare_embeddings(direct: dict, isolated: dict, report: dict) -> int:
    """Require identical metadata and exact 1280D f32 bits, not just a unit norm."""
    validate_embedding(direct, report)
    validate_embedding(isolated, report)
    fields = (
        "schema_version", "kind", "validation_status", "dimension",
        "patches_analyzed", "encoder_model", "encoder_sha256",
        "preprocessing_version", "pooling_version", "normalization_version",
        "representation_fingerprint", "audio_sha256", "track_file",
    )
    for field in fields:
        if direct.get(field) != isolated.get(field):
            raise ValueError(f"Song embedding identity mismatch: {field}")
    for index, (left, right) in enumerate(zip(
        direct["vector_f32"], isolated["vector_f32"]
    )):
        if f32_bits(left) != f32_bits(right):
            raise ValueError(f"1280D embedding f32 mismatch at dimension {index}")
    return 1280


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True, help="Built bliss-mood executable")
    parser.add_argument("--source", type=Path, required=True, help="Private source audio (read-only)")
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--models", default="moodtheme,genre,voice")
    parser.add_argument("--audio-backend", choices=["rust", "essentia"], default="rust")
    parser.add_argument("--essentia-worker", type=Path)
    parser.add_argument("--essentia-timeout-seconds", type=int, default=900)
    parser.add_argument("--max-patches", type=int)
    parser.add_argument("--embedding", action="store_true",
                        help="Compare every pooled 1280D f32 bit via hidden in-process diagnostic")
    opts = parser.parse_args()
    shared = [
        "--models-dir", str(opts.models_dir),
        "--models", opts.models,
        "--audio-backend", opts.audio_backend,
        "--essentia-timeout-seconds", str(opts.essentia_timeout_seconds),
    ]
    if opts.registry:
        shared += ["--registry", str(opts.registry)]
    if opts.essentia_worker:
        shared += ["--essentia-worker", str(opts.essentia_worker)]
    if opts.max_patches is not None:
        shared += ["--max-patches", str(opts.max_patches)]
    base = [str(opts.exe)]
    legacy = run_analysis(base + ["analyze-features", str(opts.source)] + shared + ["--json"])
    isolated_args = base + ["internal-isolated-analyze-features", str(opts.source)] + shared
    if opts.embedding:
        isolated_args.append("--embedding")
    isolated_output = run_analysis(isolated_args)
    head_count, label_count = compare_reports(legacy, isolated_output["report"])
    if opts.embedding:
        direct_output = run_analysis(
            base + ["internal-direct-analyze-features", str(opts.source)]
            + shared + ["--embedding"]
        )
        # Verify the extra in-process embedding diagnostic has not changed
        # classification outcomes compared to the original public CLI.
        compare_reports(legacy, direct_output["report"])
        compare_reports(direct_output["report"], isolated_output["report"])
        embedded = compare_embeddings(
            direct_output.get("embedding"),
            isolated_output.get("embedding"),
            legacy,
        )
    print(
        f"PASS: exact f32 classification parity for {head_count} heads, "
        f"{label_count} scores, {legacy['patches_analyzed']} patches"
        + (f"; exact {embedded}D pooled embedding f32 parity" if opts.embedding else "")
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
