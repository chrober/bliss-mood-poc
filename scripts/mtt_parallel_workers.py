#!/usr/bin/env python3
"""Bounded parallel bliss-mood workers with isolated SQLite v3 sidecars.

Only the caller downloads/extracts audio. Workers run independent
bliss-mood analyze-features processes, each writing to its own SQLite
database. Merge in a single transaction after all processes exit.
No per-track vectors, downloaded audio or track identities are published.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

HEADS = frozenset(("genre", "moodtheme"))


def analyze_one(binary: Path, models_dir: Path, sidecar: Path, key: str, audio: bytes):
    if not audio or len(audio) > 20 * 1024 * 1024:
        raise ValueError("Audio buffer missing or oversized")
    with tempfile.TemporaryDirectory(prefix="mtt-analysis-") as temp:
        local = Path(temp) / "clip.mp3"
        local.write_bytes(audio)
        cmd = [
            str(binary.resolve()), "analyze-features", str(local),
            "--models-dir", str(models_dir.resolve()),
            "--models", "genre,moodtheme", "--threads", "1",
            "--db", str(sidecar.resolve()), "--track-key", key
        ]
        completed = subprocess.run(cmd, check=False, capture_output=True,
                                   text=True, timeout=900)
        if completed.returncode:
            raise RuntimeError(
                "MTT audio inference failed (redacted, worker-sidecar only), "
                f"exit={completed.returncode}; stderr tail: "
                f"{completed.stderr[-800:]}"
            )


def combine_sidecars(paths: list[Path], target: Path, track_keys: set[str]) -> None:
    """Fail closed if any sidecar has inconsistent models or track rows."""
    if not paths or any(not f.is_file() for f in paths):
        raise FileNotFoundError("Missing private worker sidecar")
    if target.exists():
        raise FileExistsError("Refuse to overwrite aggregated sidecar")

    def verify(db: sqlite3.Connection):
        if db.execute("PRAGMA user_version").fetchone()[0] != 3:
            raise ValueError("Worker sidecar must be schema v3")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Worker sidecar failed SQLite integrity_check")
        tracks = db.execute(
            "SELECT track_file, model_id FROM feature_tracks"
        ).fetchall()
        if len(tracks) != len(set(tracks)):
            raise ValueError("Worker sidecar duplicates track/head pairs")
        if any(head not in HEADS or track not in track_keys for track, head in tracks):
            raise ValueError("Unexpected MTT track or head in private sidecar")
        grouped = {}
        for track, head in tracks:
            grouped.setdefault(track, set()).add(head)
        if any(heads != HEADS for heads in grouped.values()):
            raise ValueError("Incomplete Genre/Mood track in worker sidecar")
        models = db.execute("SELECT * FROM feature_models ORDER BY model_key").fetchall()
        if len(models) != 2:
            raise ValueError("Expected two distinct model fingerprints")
        return grouped, models

    all_tracks = set()
    reference_models = None
    for path in paths:
        with closing(sqlite3.connect(path)) as source:
            data, models = verify(source)
            if reference_models is None:
                reference_models = models
            elif models != reference_models:
                raise ValueError("Parallel workers produced inconsistent model metadata")
            if all_tracks.intersection(data):
                raise ValueError("Duplicate clip across isolated worker DBs")
            all_tracks.update(data)
    if all_tracks != track_keys:
        raise ValueError("Not all selected clips analyzed; refuse incomplete merge")

    # Copy the real Rust-generated schema verbatim, not a handwritten
    # approximation. The source DBs remain unchanged until CI cleanup.
    shutil.copyfile(paths[0], target)
    try:
        with closing(sqlite3.connect(target)) as result:
            result.execute("PRAGMA foreign_keys=ON")
            for path in paths[1:]:
                source = sqlite3.connect(path)
                try:
                    with result:
                        for table in ("feature_tracks", "feature_track_state"):
                            cols = [row[1] for row in result.execute(
                                f"PRAGMA table_info({table})"
                            )]
                            if not cols:
                                raise ValueError(f"Missing schema v3 table {table}")
                            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
                            rows = source.execute(
                                f"SELECT {', '.join(cols)} FROM {table}"
                            ).fetchall()
                            result.executemany(sql, rows)
                finally:
                    source.close()
            groups, models = verify(result)
            if set(groups) != track_keys or models != reference_models:
                raise ValueError("Merged sidecar differs from validated inputs")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def analyze_parallel(binary: Path, models_dir: Path, db: Path,
                     tasks, expected_track_keys: set[str],
                     workers: int = 2) -> dict:
    """Consume (track_key, audio_bytes) lazily, bounded by worker count.

    Caller owns the sequential network extraction, so this does not
    increase requests against the research archive.
    """
    if not 1 <= workers <= 4:
        raise ValueError("Workers must be 1..4 on bounded GH runners")
    if db.exists():
        raise FileExistsError("Refuse overwrite of existing feature sidecar")
    if not expected_track_keys:
        raise ValueError("Empty feature cohort")
    start = time.monotonic()
    sidecars = [db.parent / f"{db.stem}-worker-{i}.db" for i in range(workers)]
    if any(path.exists() for path in sidecars):
        raise FileExistsError("Stale worker sidecar present")
    active = [None] * workers
    count = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for key, audio in tasks:
            slot = count % workers
            if active[slot] is not None:
                active[slot].result()
            active[slot] = pool.submit(analyze_one, binary, models_dir,
                                       sidecars[slot], key, audio)
            count += 1
            if count % 50 == 0:
                print(f"MTT dispatched {count} clips to {workers} isolated workers",
                      flush=True)
        for future in active:
            if future is not None:
                future.result()
    if count != len(expected_track_keys):
        raise ValueError("Task count mismatch after parallel analysis")
    combine_sidecars([f for f in sidecars if f.is_file()], db, expected_track_keys)
    return {
        "clips_analyzed": count,
        "workers": workers,
        "onnx_threads_per_song": 1,
        "parallel_inference_and_merge_wall_seconds": round(time.monotonic()-start, 3),
        "isolated_worker_sidecars": len([x for x in sidecars if x.is_file()]),
    }
