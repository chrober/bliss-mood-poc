"""Read-only deterministic Mood-quality sample from a copy of bliss.db.

Calls bliss-mood analyze --json, WITHOUT any SQLite write options.
Windows:
  python scripts/sample_mood_quality.py --bliss-db .\bliss.db --source-root '\\192.168.1.100\music' --exe .\bliss-mood.exe --models-dir .\models --count 12
"""
import argparse
import csv
import json
import random
import sqlite3
import subprocess
import sys
from pathlib import Path


def normalize_track_key(key):
    parts = key.replace("\\", "/").split("/")
    if not parts or any(part in ("", ".", "..") or ":" in part for part in parts):
        raise ValueError(f"Unsafe relative music path: {key!r}")
    if key.startswith(("/", "\\")):
        raise ValueError(f"Absolute music path rejected: {key!r}")
    return parts


def select_keys(bliss_db, count, seed):
    database = Path(bliss_db).resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Bliss database copy missing: {database}")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        keys = [key for (key,) in db.execute(
            "SELECT File FROM TracksV2 WHERE Ignore IS NOT 1 ORDER BY File"
        ) if key]
    return random.Random(seed).sample(keys, min(count, len(keys))), len(keys)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bliss-db", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, required=True)
    p.add_argument("--count", type=int, default=12)
    p.add_argument("--seed", type=int, default=20261018)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--timeout-seconds", type=int, default=180)
    p.add_argument("--output", type=Path, default=Path("mood-quality-sample.csv"))
    args = p.parse_args()
    if args.count < 1 or args.count > 100 or args.threads < 1:
        p.error("--count must be 1..100 and --threads must be positive")
    if not args.exe.is_file():
        p.error(f"Executable missing: {args.exe}")
    metadata = json.loads(
        (args.models_dir / "mtg_jamendo_moodtheme-discogs-effnet-1.json").read_text(encoding="utf-8")
    )
    classes = metadata["classes"]
    if len(classes) != 56 or len(set(classes)) != 56:
        p.error("Expected 56 unique classifier labels")

    keys, total = select_keys(args.bliss_db, args.count, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    columns = ("track_key", "status", "error", "total_seconds", "patches",
               "preprocessing_version", "top5") + tuple(classes)
    success = 0
    with args.output.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        for i, key in enumerate(keys, 1):
            row = {"track_key": key, "status": "error", "error": ""}
            try:
                path = args.source_root.joinpath(*normalize_track_key(key))
                if not path.is_file():
                    raise FileNotFoundError(str(path))
                command = [
                    str(args.exe.resolve()), "analyze", str(path),
                    "--models-dir", str(args.models_dir.resolve()),
                    "--threads", str(args.threads), "--json",
                ]
                result = subprocess.run(
                    command, check=True, capture_output=True,
                    text=True, encoding="utf-8", timeout=args.timeout_seconds
                )
                data = json.loads(result.stdout)
                if set(data["scores"]) != set(classes):
                    raise ValueError("Classifier labels don't match model metadata")
                row.update({
                    "status": "ok",
                    "total_seconds": round(data["timings"]["total_seconds"], 3),
                    "patches": data["patches_analyzed"],
                    "preprocessing_version": data["preprocessing_version"],
                    "top5": ", ".join(f"{k}={v:.3f}" for k, v in sorted(
                        data["scores"].items(), key=lambda pair: -pair[1]
                    )[:5]),
                    **data["scores"],
                })
                success += 1
            except (OSError, ValueError, KeyError,
                    subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                row["error"] = str(exc)[:400]
            writer.writerow(row)
            fp.flush()
            print(f"[{i}/{len(keys)}] {row['status']}: {key}", file=sys.stderr)
    print(f"Selected {len(keys)} of {total} eligible tracks; {success} succeeded. "
          f"Output: {args.output}")
    if success != len(keys):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
