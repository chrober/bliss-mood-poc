#!/usr/bin/env python3
"""Read official FMA metadata ZIP without downloading or processing audio.

Inventory the FMA-Small 8-class genre cohort, official train/val/test
split counts and artist group overlap. Aggregate-only public JSON; never
export filenames, artist names, recording IDs or private user music.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import zipfile

FMA_SOURCE = "https://github.com/mdeff/fma"
SMALL = "small"


def inspect(archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist()
                 if Path(name).name == "tracks.csv"]
        if len(names) != 1:
            raise ValueError("Exactly one FMA tracks.csv expected")
        with archive.open(names[0]) as stream:
            import io
            csv.field_size_limit(16 * 1024 * 1024)
            reader = csv.reader(io.TextIOWrapper(
                stream, encoding="utf-8-sig", newline=""
            ))
            try:
                groups = next(reader)
                fields = next(reader)
            except StopIteration as err:
                raise ValueError("FMA metadata lacks two header rows") from err
            if len(groups) != len(fields):
                raise ValueError("Malformed FMA multi-index header")
            columns = {
                (g.strip().casefold(), f.strip().casefold()): idx
                for idx, (g, f) in enumerate(zip(groups, fields))
            }
            required = (
                ("set", "subset"), ("set", "split"),
                ("track", "genre_top"), ("artist", "id"),
            )
            missing = [name for name in required if name not in columns]
            if missing:
                raise ValueError(f"Missing FMA tracks.csv columns: {missing}")
            if not fields or fields[0].strip().casefold() not in ("", "track_id"):
                # Index values are numeric FMA track IDs.
                raise ValueError("Unexpected FMA track-id index column")
            matched = 0
            seen_ids = set()
            genres: Counter[str] = Counter()
            splits: Counter[str] = Counter()
            class_by_split: dict[str, Counter[str]] = defaultdict(Counter)
            artist_sets: dict[str, set[str]] = defaultdict(set)
            missing_artist = 0
            invalid_rows = 0
            for row in reader:
                if not row:
                    continue
                if len(row) != len(groups):
                    invalid_rows += 1
                    continue
                subset = row[columns[("set", "subset")]].strip().lower()
                if subset != SMALL:
                    continue
                try:
                    ident = str(int(row[0]))
                    if int(ident) <= 0:
                        raise ValueError("Invalid ID")
                except (ValueError, TypeError):
                    invalid_rows += 1
                    continue
                if ident in seen_ids:
                    raise ValueError("Duplicate FMA-Small track ID")
                seen_ids.add(ident)
                genre = row[columns[("track", "genre_top")]].strip()
                split = row[columns[("set", "split")]].strip().lower()
                artist = row[columns[("artist", "id")]].strip()
                if not genre or split not in ("training", "validation", "test"):
                    invalid_rows += 1
                    continue
                matched += 1
                genres[genre] += 1
                splits[split] += 1
                class_by_split[split][genre] += 1
                if artist:
                    artist_sets[split].add(artist)
                else:
                    missing_artist += 1
    if matched < 1:
        raise ValueError("No valid FMA-Small metadata rows")
    train = artist_sets["training"]
    valid = artist_sets["validation"]
    test = artist_sets["test"]
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as input_file:
            for piece in iter(lambda: input_file.read(1024 * 1024), b""):
                digest.update(piece)
        return digest.hexdigest()
    return {
        "schema": "fma-small-metadata-audit-v1",
        "source": FMA_SOURCE,
        "data": {"subset": "small", "track_count": matched,
                 "genres": dict(sorted(genres.items())),
                 "splits": dict(sorted(splits.items())),
                 "genre_by_split": {
                     split: dict(sorted(class_by_split[split].items()))
                     for split in ("training", "validation", "test")
                 },
                 "artist_count_by_split": {
                     split: len(artist_sets[split])
                     for split in ("training", "validation", "test")
                 },
                 "artists_in_multiple_splits": {
                     "training_validation": len(train & valid),
                     "training_test": len(train & test),
                     "validation_test": len(valid & test),
                 },
                 "missing_artist_rows": missing_artist,
                 "invalid_small_rows": invalid_rows},
        "metadata_zip_sha256": sha256(archive_path),
        "caveats": [
            "Top-level FMA genres are coarse similarity proxies, not human pairwise judgments.",
            "Artist disjointness across splits requires verifying official metadata; reported here.",
            "Any later benchmark must use only split-correct tracks and independent track audio.",
            "FMA song-level genre does not provide human mood similarity reference labels.",
            "All audio licenses and original FMA source terms must be checked for further use.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.metadata_zip.is_file():
        parser.error("Missing FMA metadata ZIP")
    if args.output.exists():
        parser.error("Output exists; never overwrite an existing benchmark report")
    report = inspect(args.metadata_zip)
    n = report["data"]["track_count"]
    if n < 7000 or n > 8500:
        raise ValueError(f"Unexpected FMA-Small cohort size: {n}")
    if len(report["data"]["genres"]) != 8:
        raise ValueError("Expected exactly 8 official FMA-Small top-level genres")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({"track_count": n, "genres": report["data"]["genres"],
                      "splits": report["data"]["splits"],
                      "artists_in_multiple_splits":
                          report["data"]["artists_in_multiple_splits"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
