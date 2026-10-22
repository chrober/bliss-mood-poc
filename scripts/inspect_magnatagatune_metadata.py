#!/usr/bin/env python3
"""Audio-free, fail-closed MagnaTagATune metadata and vote schema preflight.

No identity-level clip/artist/track outputs. A schema inventory is NOT a
validated triplet benchmark; identify the actual released column names
before implementing a majority-vote parser and ordering held-out questions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import time

SOURCE = "https://mirg.city.ac.uk/datasets/magnatagatune/"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def field_label(key: str) -> str:
    return re.sub(r"\s+", " ", key.strip()).casefold()


def profile(path: Path, expected_min: int, max_file_mb: int = 30) -> dict:
    if not path.is_file() or path.stat().st_size > max_file_mb * 1024 * 1024:
        raise ValueError("Missing or unexpectedly large MTT metadata CSV")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(2048)
        stream.seek(0)
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
        except csv.Error:
            delim = ","
        reader = csv.DictReader(stream, delimiter=delim)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("Missing or duplicate MTT metadata headers")
        if len(headers) < 2 or len(headers) > 40:
            raise ValueError("Implausible MTT metadata schema")
        if any(not k.strip() for k in headers):
            raise ValueError("Empty column in MTT metadata")
        # Aggregate only; keys are names of official metadata columns.
        row_count = 0
        blanks = Counter()
        numeric = Counter()
        unique_limited = {name: set() for name in headers}
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Malformed MTT CSV with inconsistent column counts")
            row_count += 1
            for name in headers:
                value = row[name].strip()
                if not value:
                    blanks[name] += 1
                    continue
                try:
                    number = float(value)
                    if math.isfinite(number):
                        numeric[name] += 1
                except ValueError:
                    pass
                # Cap memory and avoid encoding private identifiers in output.
                if len(unique_limited[name]) < 50000:
                    unique_limited[name].add(value)
        if row_count < expected_min:
            raise ValueError(f"Only {row_count} rows; expected at least {expected_min}")
    return {
        "rows": row_count,
        "fields": headers,
        "delimiter": {",": "comma", ";": "semicolon", "\t": "tab"}[delim],
        "blank_rows_per_field": dict(blanks),
        "numeric_rows_per_field": dict(numeric),
        "distinct_values_per_field_upper_capped_at_50000": {
            name: len(values) for name, values in unique_limited.items()
        },
        "sha256": digest(path),
        "bytes": path.stat().st_size,
    }


def inspect(comparisons: Path, clips: Path) -> dict:
    start = time.monotonic()
    return {
        "schema": "magnatagatune-official-metadata-preflight-v1",
        "source": SOURCE,
        "comparison_data": profile(comparisons, expected_min=100),
        "clip_data": profile(clips, expected_min=1000),
        "runtime": {"wall_seconds": round(time.monotonic() - start, 3)},
        "status": "schema_inventory_only_not_yet_verified_triplet_vote_parsing",
        "warnings": [
            "No audio read, downloaded, analyzed or redistributed by the parser.",
            "Column names and distinct counts are not human similarity agreement.",
            "Exact odd-one-out vote encoding, clip identity, ties and missing votes require a follow-up schema-specific validated parser.",
            "Do not infer a musical similarity score or choose a metric from this schema inventory.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Report path already exists")
    result = inspect(args.comparisons, args.clips)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "schema": result["schema"],
        "comparison_rows": result["comparison_data"]["rows"],
        "comparison_columns": result["comparison_data"]["fields"],
        "clip_rows": result["clip_data"]["rows"],
        "clip_columns": result["clip_data"]["fields"],
        "parser_wall_seconds": result["runtime"]["wall_seconds"],
        "status": result["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
