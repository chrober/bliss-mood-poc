#!/usr/bin/env python3
"""Local-only, bounded native Essentia fixed-vs-adaptive worker benchmark.

Uses a deliberately sampled Bliss TracksV2 cohort (30..500 entries) and
new independent feature sidecars. Never uploads music or reports to CI.
This is an observational benchmark, not simulated adaptive telemetry.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import time

from benchmark_audio_backends import (
    checked_cohort, digest, load_feature_rows, model_fingerprints_by_head,
    validate_report, validate_source_roots,
)
from verify_manifest_batch_smoke import stored_embeddings


def schedule(repeats: int, seed: int) -> list[tuple[int, str]]:
    modes = ["fixed1", "fixed2", "fixed4", "fixed6", "adaptive2"]
    rng = random.Random(seed)
    rng.shuffle(modes)
    return [
        (repeat + 1, mode)
        for repeat in range(repeats)
        for mode in (modes if repeat % 2 == 0 else list(reversed(modes)))
    ]


def analyze(args: argparse.Namespace, round_no: int, mode: str,
            expected: int) -> tuple[dict, dict, dict]:
    is_adaptive = mode == "adaptive2"
    workers = 2 if is_adaptive else int(mode.removeprefix("fixed"))
    stem = f"round-{round_no:02d}-{mode}"
    db = args.output_dir / f"{stem}.sqlite"
    embedding_dir = args.output_dir / f"{stem}-embeddings"
    stdout_path = args.output_dir / f"{stem}.scanner.json"
    stderr_path = args.output_dir / f"{stem}.stderr.txt"
    if db.exists() or embedding_dir.exists() or stdout_path.exists() or stderr_path.exists():
        raise FileExistsError(f"Will not reuse or overwrite benchmark output: {stem}")
    embedding_dir.mkdir()
    cmd = [
        str(args.analyzer), "scan-features",
        "--bliss-db", str(args.cohort_db), "--db", str(db),
        "--embedding-dir", str(embedding_dir),
        "--models-dir", str(args.models_dir),
        "--models", args.models,
        "--audio-backend", "essentia",
        "--essentia-worker", str(args.essentia_worker),
        "--essentia-timeout-seconds", str(args.timeout_seconds),
        "--workers", str(workers),
        "--threads", "1",
        "--max-new", str(expected), "--max-errors", "1", "--json",
    ]
    if args.source_root:
        cmd.extend(["--source-root", str(args.source_root)])
    if args.library_root:
        cmd.extend(["--library-root", args.library_root])
    if is_adaptive:
        cmd.extend(["--adaptive-workers", "--min-workers", "1", "--max-workers", "6"])
    start = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open(
        "w", encoding="utf-8"
    ) as err:
        proc = subprocess.run(cmd, stdout=out, stderr=err, check=False)
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(f"{stem} failed (exit {proc.returncode}); inspect {stderr_path}")
    summary = json.loads(stdout_path.read_text(encoding="utf-8"))
    validate_report(summary, expected)
    diag = summary.get("diagnostics") or {}
    baseline_s = (diag.get("baseline") or {}).get("cpu_measurement_seconds") or 0
    if not 0 <= baseline_s < elapsed or not math.isfinite(elapsed):
        raise AssertionError("Invalid wall time or resource-baseline measurement")
    adjustments = diag.get("adjustments", [])
    if not isinstance(adjustments, list):
        raise AssertionError("Malformed native adaptive diagnostics")
    if is_adaptive:
        if diag.get("initial_workers") != 2 or not 1 <= diag.get("final_workers", 0) <= 6:
            raise AssertionError("Invalid adaptive worker bounds")
    elif adjustments:
        raise AssertionError("Fixed worker run unexpectedly changed worker count")
    record = {
        "round": round_no, "mode": mode, "initial_workers": workers,
        "tracks": expected, "wall_seconds": round(elapsed, 3),
        "songs_per_minute": round(expected * 60 / elapsed, 3),
        "preworker_cpu_baseline_seconds": round(baseline_s, 3),
        "wall_excluding_preworker_baseline_seconds": round(elapsed - baseline_s, 3),
        "scan_seconds": round(summary.get("elapsed_seconds", 0), 3),
        "peak_active_analyses": diag.get("peak_active_analyses"),
        "peak_in_flight": diag.get("peak_in_flight"),
        "final_workers": diag.get("final_workers"),
        "adjustments": len(adjustments),
        "system_cpu_average_percent": diag.get("system_cpu_average_percent"),
        "system_cpu_max_percent": diag.get("system_cpu_max_percent"),
        "system_ram_max_percent": diag.get("system_ram_max_percent"),
        "process_tree_private_mib_max": diag.get("process_tree_private_bytes_max_mib"),
        "process_tree_incomplete_samples": diag.get("process_tree_incomplete_samples"),
        "native_child_processes_max": diag.get("native_child_processes_max"),
    }
    # Exact parity remains mandatory across all fixed/adaptive run orders.
    return record, load_feature_rows(db), {
        "vectors": stored_embeddings(embedding_dir, args.cohort),
        "fingerprints": model_fingerprints_by_head(db),
    }


def summarize(runs: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in runs:
        groups[item["mode"]].append(item)
    return [
        {
            "mode": mode,
            "repeats": len(group),
            "median_wall_seconds": round(
                statistics.median(g["wall_seconds"] for g in group), 3),
            "median_songs_per_minute": round(
                statistics.median(g["songs_per_minute"] for g in group), 3),
            "peak_process_tree_private_mib": max(
                (g["process_tree_private_mib_max"] for g in group
                 if g["process_tree_private_mib_max"] is not None),
                default=None),
            "observed_adaptive_adjustments": sum(g["adjustments"] for g in group),
        }
        for mode, group in sorted(groups.items())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-db", required=True, type=Path,
                        help="An existing bounded TracksV2 cohort DB; never a full-library DB")
    parser.add_argument("--analyzer", required=True, type=Path)
    parser.add_argument("--essentia-worker", required=True, type=Path)
    parser.add_argument("--models-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--library-root")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--models", default="moodtheme,genre,voice")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.repeats not in (2, 4):
        parser.error("--repeats must be 2 or 4 for balanced run order")
    if not 1 <= args.timeout_seconds <= 7200:
        parser.error("--timeout-seconds must be 1..7200")
    if not args.models or len(set(args.models.split(","))) != len(args.models.split(",")):
        parser.error("Duplicate/empty model names are not allowed")
    try:
        validate_source_roots(args.source_root, args.library_root)
        cohort = checked_cohort(args.cohort_db)
    except ValueError as error:
        parser.error(str(error))
    if len(cohort) < 30:
        parser.error("Adaptive evaluation requires a deliberate 30..500-track cohort")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Output directory must be new/empty; never overwrite prior runs")
    for item in (args.analyzer, args.essentia_worker):
        if not item.is_file():
            parser.error(f"Missing executable: {item}")
    if not args.models_dir.is_dir():
        parser.error("Missing ONNX model directory")
    plan = schedule(args.repeats, args.seed)
    print("Local, private, bounded experiment plan:")
    print(json.dumps({"tracks": len(cohort), "order": plan,
                      "note": "No music or private database contents uploaded"},
                     indent=2))
    if args.plan_only:
        return
    args.cohort = cohort
    args.analyzer = args.analyzer.resolve()
    args.essentia_worker = args.essentia_worker.resolve()
    args.cohort_db = args.cohort_db.resolve()
    args.models_dir = args.models_dir.resolve()
    if args.source_root:
        args.source_root = args.source_root.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    original_cohort_hash = digest(args.cohort_db)
    manifest = {
        "cohort_tracks": len(cohort),
        "cohort_database_sha256": original_cohort_hash,
        "analyzer_sha256": digest(args.analyzer),
        "native_worker_sha256": digest(args.essentia_worker),
        "models": args.models,
        "schedule": plan,
        "note": "PRIVATE LOCAL BENCHMARK; never commit or upload outputs",
    }
    (args.output_dir / "experiment.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    reference_scores = reference_vectors = reference_models = None
    records: list[dict] = []
    for ordinal, (round_no, mode) in enumerate(plan, start=1):
        rec, scores, extra = analyze(args, round_no, mode, len(cohort))
        if reference_scores is None:
            reference_scores = scores
            reference_vectors = extra["vectors"]
            reference_models = extra["fingerprints"]
        elif (scores != reference_scores or
              extra["vectors"] != reference_vectors or
              extra["fingerprints"] != reference_models):
            raise AssertionError(
                f"Native fixed/adaptive numerical parity drift at {mode}, "
                f"round {round_no}; results remain LOCAL in {args.output_dir}")
        records.append(rec)
        (args.output_dir / "summary.json").write_text(
            json.dumps({"experiment": manifest, "runs": records,
                        "aggregates": summarize(records),
                        "exact_numeric_parity": True},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"PASS {ordinal}/{len(plan)} {mode}: {rec['wall_seconds']:.2f}s; "
              f"resizes={rec['adjustments']}", flush=True)
    if digest(args.cohort_db) != original_cohort_hash:
        raise AssertionError("Read-only input Bliss cohort DB unexpectedly changed")
    with (args.output_dir / "runs.csv").open("w", newline="", encoding="utf-8") as csvout:
        writer = csv.DictWriter(csvout, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"PASS balanced fixed/adaptive benchmark, exact parity: {args.output_dir}")


if __name__ == "__main__":
    main()
