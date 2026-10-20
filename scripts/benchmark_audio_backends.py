#!/usr/bin/env python3
"""Reproducible Windows/Linux A/B benchmark of Rust and native Essentia DSP.

Uses the existing Rust scan-features orchestrator for BOTH backends and
separate fresh schema-v3 SQLite sidecars. Does not alter Bliss or audio.
Sample cohort MUST be an existing bounded TracksV2 database, preferably
the repository's documented 100-key fixture generated on the user's PC.
Never run against the full 64,000-track library without selecting a cohort.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3
import statistics
import struct
import subprocess
import sys
import time

MAX_SAMPLE_TRACKS = 500
VALID_WORKERS = (1, 2, 4, 6, 8, 10, 12)


def checked_cohort(path):
    if not path.is_file():
        raise ValueError(f"Missing cohort database: {path}")
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        query = ("SELECT File FROM TracksV2 "
                 "WHERE Ignore IS NOT 1 ORDER BY File")
        rows = [row[0] for row in conn.execute(query)]
    finally:
        conn.close()
    if not 2 <= len(rows) <= MAX_SAMPLE_TRACKS:
        raise ValueError(
            f"Require a deliberate 2..{MAX_SAMPLE_TRACKS}-track Bliss cohort; "
            f"found {len(rows)} eligible tracks. Never benchmark all LMS tracks."
        )
    if len(set(rows)) != len(rows):
        raise ValueError("Cohort contains duplicate Bliss track identity")
    return rows


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def experiment_plan(worker_counts, repeats, seed):
    """AB / BA order per repeat and shuffled worker order for cache fairness."""
    randomizer = random.Random(seed)
    runs = []
    for round_index in range(repeats):
        counts = list(worker_counts)
        randomizer.shuffle(counts)
        backend_order = ("rust", "essentia") if round_index % 2 == 0 else (
            "essentia", "rust"
        )
        for worker_count in counts:
            for backend in backend_order:
                runs.append((round_index + 1, worker_count, backend))
    return runs


def load_feature_rows(db):
    with sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True) as conn:
        records = conn.execute(
            "SELECT track_file, model_id, patches_analyzed, scores_f32_le "
            "FROM feature_tracks ORDER BY track_file, model_id"
        ).fetchall()
    result = {}
    for track, model, count, blob in records:
        if not blob or len(blob) % 4:
            raise AssertionError("Invalid feature row shape")
        values = struct.unpack(f"<{len(blob)//4}f", blob)
        if count <= 0 or not all(math.isfinite(x) for x in values):
            raise AssertionError("Nonfinite scores or invalid patch count")
        result[track, model] = (count, values)
    return result


def compare_feature_tables(baseline, alternative):
    """Compare identical keys/classes, NEVER require identical model keys."""
    if baseline.keys() != alternative.keys():
        missing = sorted(baseline.keys() - alternative.keys())
        extra = sorted(alternative.keys() - baseline.keys())
        raise AssertionError(
            f"Different analyzed cohorts: missing={len(missing)}, extra={len(extra)}"
        )
    max_error, sum_error, observations = 0.0, 0.0, 0
    count_mismatches = 0
    for key in baseline:
        a_count, a = baseline[key]
        b_count, b = alternative[key]
        if a_count != b_count:
            count_mismatches += 1
        if len(a) != len(b):
            raise AssertionError(f"Class-vector dimension mismatch: {key}")
        diffs = [abs(x - y) for x, y in zip(a, b)]
        max_error = max(max_error, *diffs)
        sum_error += sum(diffs)
        observations += len(diffs)
    return {
        "tracks_and_heads": len(baseline),
        "compared_scores": observations,
        "patch_count_mismatches": count_mismatches,
        "maximum_absolute_score_difference": max_error,
        "mean_absolute_score_difference": sum_error / observations if observations else None,
    }


def validate_report(report, expected):
    if (report.get("analyzed") != expected or report.get("failures") != 0
            or report.get("missing_files") != 0):
        raise AssertionError(
            f"Scan incomplete: analyzed={report.get('analyzed')} "
            f"failures={report.get('failures')} "
            f"missing={report.get('missing_files')}; expected={expected}"
        )
    if report.get("pending") != expected:
        raise AssertionError("Scan did not attempt exactly the expected cohort")


def run_scan(args, round_index, workers, backend, expected):
    stem = f"round-{round_index:02d}-workers-{workers:02d}-{backend}"
    db = args.output_dir / (stem + ".db")
    result_file = args.output_dir / (stem + ".json")
    err_file = args.output_dir / (stem + ".stderr.txt")
    if db.exists() or result_file.exists() or err_file.exists():
        raise FileExistsError(f"Refusing to overwrite benchmark artifacts for {stem}")
    cmd = [
        str(args.analyzer), "scan-features",
        "--bliss-db", str(args.cohort_db),
        "--db", str(db),
        "--models-dir", str(args.models_dir),
        "--models", args.models,
        "--workers", str(workers),
        "--threads", "1",
        "--max-errors", "1",
        "--max-new", str(expected),
        "--audio-backend", backend,
        "--json",
    ]
    if args.source_root:
        cmd.extend(["--source-root", str(args.source_root)])
    if args.library_root:
        cmd.extend(["--library-root", args.library_root])
    if backend == "essentia":
        cmd.extend([
            "--essentia-worker", str(args.essentia_worker),
            "--essentia-timeout-seconds", str(args.timeout_seconds),
        ])
    start = time.perf_counter()
    with result_file.open("w", encoding="utf-8") as out, err_file.open(
        "w", encoding="utf-8"
    ) as error:
        result = subprocess.run(cmd, stdout=out, stderr=error, check=False)
    elapsed = time.perf_counter() - start
    if result.returncode:
        raise RuntimeError(
            f"{stem} failed (exit {result.returncode}); inspect {err_file}"
        )
    report = json.loads(result_file.read_text(encoding="utf-8"))
    validate_report(report, expected)
    details = report.get("diagnostics") or {}
    scan = {
        "round": round_index, "workers": workers, "backend": backend,
        "tracks": expected, "seconds": elapsed,
        "songs_per_minute": 60.0 * expected / elapsed,
        "reported_scan_seconds": report["elapsed_seconds"],
        "cpu_average_percent": details.get("system_cpu_average_percent"),
        "system_ram_max_percent": details.get("system_ram_max_percent"),
        "rust_working_set_mib": details.get("process_working_set_max_mib"),
        "process_tree_working_set_mib":
            details.get("process_tree_working_set_max_mib"),
        "process_tree_private_bytes_mib":
            details.get("process_tree_private_bytes_max_mib"),
        "native_children_max": details.get("native_child_processes_max"),
        "incomplete_memory_samples":
            details.get("process_tree_incomplete_samples"),
        "sqlite": db.name, "report": result_file.name,
    }
    if not math.isfinite(elapsed) or elapsed <= 0.0:
        raise AssertionError("Invalid wall-clock measurement")
    return scan, load_feature_rows(db)


def matrix_aggregate(runs):
    groups = {}
    for record in runs:
        groups.setdefault((record["workers"], record["backend"]), []).append(record)
    data = []
    for (workers, backend), entries in sorted(groups.items()):
        data.append({
            "workers": workers,
            "backend": backend,
            "runs": len(entries),
            "median_seconds": statistics.median(x["seconds"] for x in entries),
            "median_songs_per_minute": statistics.median(
                x["songs_per_minute"] for x in entries),
            "max_process_tree_working_set_mib": max(
                (x["process_tree_working_set_mib"]
                 for x in entries if x["process_tree_working_set_mib"] is not None),
                default=None),
            "max_system_ram_percent": max(
                (x["system_ram_max_percent"] for x in entries
                 if x["system_ram_max_percent"] is not None),
                default=None),
        })
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-db", required=True, type=Path,
                        help="Prebuilt bounded Bliss TracksV2 subset, e.g. sample-100.db")
    parser.add_argument("--analyzer", required=True, type=Path)
    parser.add_argument("--essentia-worker", required=True, type=Path)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--library-root")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--models", default="moodtheme,genre,voice")
    parser.add_argument("--workers", default="1,2,4,6")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--score-max-tolerance", type=float, default=1e-3)
    args = parser.parse_args()
    if args.repeats not in (1, 2, 3, 4):
        parser.error("--repeats must be between 1 and 4")
    if args.timeout_seconds not in range(1, 7201):
        parser.error("--timeout-seconds must be 1..7200")
    try:
        counts = [int(i) for i in args.workers.split(",")]
    except ValueError:
        parser.error("--workers must be comma-separated integers")
    if not counts or len(counts) != len(set(counts)) or any(
        count not in VALID_WORKERS for count in counts
    ):
        parser.error(f"--workers must be unique values from {VALID_WORKERS}")
    if not 0 < args.score_max_tolerance < 0.1:
        parser.error("--score-max-tolerance must be between zero and 0.1")
    if bool(args.library_root) != bool(args.source_root):
        parser.error("Use --library-root with --source-root, or neither")
    for name, path in [("analyzer", args.analyzer),
                       ("Essentia worker", args.essentia_worker)]:
        if not path.is_file():
            parser.error(f"Missing {name} executable: {path}")
    if not args.models_dir.is_dir():
        parser.error("Missing models directory")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Output directory must be new or empty (fresh sidecars)")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.analyzer = args.analyzer.resolve()
    args.essentia_worker = args.essentia_worker.resolve()
    args.cohort_db = args.cohort_db.resolve()
    args.models_dir = args.models_dir.resolve()
    if args.source_root:
        args.source_root = args.source_root.resolve()

    cohort = checked_cohort(args.cohort_db)
    original_cohort_sha = digest(args.cohort_db)
    manifest = {
        "schema_version": 1, "cohort_size": len(cohort),
        "cohort_database_sha256": original_cohort_sha,
        "analyzer_binary_sha256": digest(args.analyzer),
        "essentia_worker_binary_sha256": digest(args.essentia_worker),
        "models": args.models, "worker_counts": counts,
        "repeats": args.repeats, "seed": args.seed,
        "backend_order": "AB/BA per repeat, worker counts shuffled",
        "note": "Synthetic/test or private library only; do not commit output artifacts",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    runs, comparisons = [], []
    for round_index, count, backend in experiment_plan(
        counts, args.repeats, args.seed
    ):
        record, scores = run_scan(args, round_index, count, backend, len(cohort))
        runs.append(record)
        print(f"{backend:8} workers={count} run={round_index}: "
              f"{record['seconds']:.2f}s; "
              f"{record['songs_per_minute']:.1f} tracks/min", flush=True)
        partner = next((r for r in runs[:-1] if r["round"] == round_index
                        and r["workers"] == count and r["backend"] != backend), None)
        if partner:
            prior = load_feature_rows(args.output_dir / partner["sqlite"])
            baseline, native = (scores, prior) if backend == "rust" else (prior, scores)
            comp = compare_feature_tables(baseline, native)
            comp.update({"workers": count, "round": round_index})
            comparisons.append(comp)
            if comp["patch_count_mismatches"] or (
                comp["maximum_absolute_score_difference"]
                > args.score_max_tolerance
            ):
                raise AssertionError(
                    f"Backend drift at {count} workers, round {round_index}: {comp}"
                )

    if digest(args.cohort_db) != original_cohort_sha:
        raise AssertionError("Input Bliss cohort database changed; benchmark invalid")
    summary = {
        "manifest": manifest,
        "runs": runs,
        "aggregates": matrix_aggregate(runs),
        "backend_parity": comparisons,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if runs:
        with (args.output_dir / "runs.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(runs[0]))
            writer.writeheader()
            writer.writerows(runs)
    print(f"Benchmark and backend score parity PASS: {args.output_dir}")


if __name__ == "__main__":
    main()
