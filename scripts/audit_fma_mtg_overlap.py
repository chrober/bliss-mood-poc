#!/usr/bin/env python3
"""Metadata-only, conservative FMA-Small vs MTG-Jamendo catalog overlap.

Screens official FMA TRAINING and VALIDATION artist/title metadata only.
Deliberately DOES NOT inspect FMA TEST artist/title or evaluate any audio.
Exact NFKD-folded artist+title matches are possible catalog overlaps,
NOT identified shared recordings, training examples, or model leakage.
Artist-only matches are even weaker provenance signals.
Exports only aggregate counts, schema and source file hashes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from audit_deam_mtg_overlap import clean, load_mtg_metadata

SCHEMA = "fma-small-mtg-jamendo-catalog-overlap-v1"
SPLITS = ("training", "validation")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def read_fma_development_metadata(archive_path: Path):
    """Return sanitized in-memory development records, never FMA TEST labels.

    Artist ID is for duplicate-identity diagnostics only. All source
    identifiers, names, titles and keys are discarded from public reports.
    """
    with zipfile.ZipFile(archive_path) as archive:
        csv_members = [x for x in archive.namelist() if Path(x).name == "tracks.csv"]
        if len(csv_members) != 1:
            raise ValueError("Expected exactly one official FMA tracks.csv")
        with archive.open(csv_members[0]) as stream:
            csv.field_size_limit(16 * 1024 * 1024)
            reader = csv.reader(io.TextIOWrapper(
                stream, encoding="utf-8-sig", errors="replace", newline=""
            ))
            try:
                groups, fields = next(reader), next(reader)
            except StopIteration as e:
                raise ValueError("FMA tracks.csv missing double header") from e
            if len(groups) != len(fields):
                raise ValueError("Invalid FMA multi-index header lengths")
            cols = {(g.strip().casefold(), k.strip().casefold()): i
                    for i, (g, k) in enumerate(zip(groups, fields))}
            required = [
                ("set", "subset"), ("set", "split"),
                ("track", "genre_top"), ("track", "title"),
                ("artist", "name"), ("artist", "id"),
            ]
            missing = [col for col in required if col not in cols]
            if missing:
                raise ValueError("FMA metadata missing required artist/title/split columns")
            result = []
            counts = Counter()
            ignored_test = 0
            ids = set()
            artist_ids = defaultdict(set)
            malformed = 0
            for row in reader:
                if len(row) != len(groups):
                    malformed += 1
                    continue
                if row[cols[("set", "subset")]].strip().casefold() != "small":
                    continue
                split = row[cols[("set", "split")]].strip().casefold()
                if split == "test":
                    # FMA test split is reserved. Do not inspect any
                    # artist/title/genre information in these rows.
                    ignored_test += 1
                    continue
                if split not in SPLITS:
                    raise ValueError("Unknown FMA-Small official split")
                ident = row[0].strip()
                artist_id = row[cols[("artist", "id")]].strip()
                genre = row[cols[("track", "genre_top")]].strip()
                if not ident.isdigit() or int(ident) <= 0 or not artist_id or not genre:
                    raise ValueError("Invalid development FMA song ID, genre or artist")
                if ident in ids:
                    raise ValueError("Duplicate FMA development track ID")
                ids.add(ident)
                counts[split] += 1
                artist_ids[split].add(artist_id)
                title = clean(row[cols[("track", "title")]].strip())
                artist = clean(row[cols[("artist", "name")]].strip())
                if (not title or not artist or title in ("unknown", "untitled")
                        or artist in ("unknown", "various artists")):
                    result.append((split, genre, None))
                else:
                    result.append((split, genre, (artist, title)))
    if not result or not all(counts[split] for split in SPLITS):
        raise ValueError("No complete FMA training/validation records")
    if malformed:
        raise ValueError("Malformed official tracks.csv records")
    if artist_ids["training"] & artist_ids["validation"]:
        raise ValueError("Unexpected artist-ID overlap across FMA development splits")
    return result, {"training": counts["training"],
                    "validation": counts["validation"],
                    "test_metadata_rows_not_inspected": ignored_test,
                    "artist_id_overlap_training_validation": 0}


def inspect(fma_metadata_zip: Path, mtg_metadata_tsv: Path) -> dict:
    fma, counts = read_fma_development_metadata(fma_metadata_zip)
    mtg_pairs, mtg_rows = load_mtg_metadata(mtg_metadata_tsv)
    mtg_artists = {artist for artist, _ in mtg_pairs}
    by_split = {split: Counter() for split in SPLITS}
    by_genre = {split: defaultdict(Counter) for split in SPLITS}
    for split, genre, pair in fma:
        bucket = by_split[split]
        subgroup = by_genre[split][genre]
        bucket["development_rows"] += 1
        subgroup["development_rows"] += 1
        if pair is None:
            bucket["no_usable_artist_title"] += 1
            subgroup["no_usable_artist_title"] += 1
            continue
        bucket["joinable_artist_title"] += 1
        subgroup["joinable_artist_title"] += 1
        if pair in mtg_pairs:
            bucket["possible_exact_artist_title_catalog_matches"] += 1
            subgroup["possible_exact_artist_title_catalog_matches"] += 1
        if pair[0] in mtg_artists:
            bucket["possible_artist_only_catalog_matches"] += 1
            subgroup["possible_artist_only_catalog_matches"] += 1

    def serial(counter):
        return {field: counter[field] for field in (
            "development_rows", "joinable_artist_title",
            "no_usable_artist_title",
            "possible_exact_artist_title_catalog_matches",
            "possible_artist_only_catalog_matches"
        )}

    return {
        "schema": SCHEMA,
        "status": "catalog_only_possible_matches_NOT_verified_ONNX_training_disjointness",
        "datasets": {
            "fma": "https://github.com/mdeff/fma",
            "mtg_jamendo": "https://github.com/MTG/mtg-jamendo-dataset",
        },
        "policy": {
            "fma_splits_inspected": list(SPLITS),
            "fma_official_test": "untouched_artist_title_genre_metadata_and_audio",
            "method": "artist_and_title_NFKD_accent_fold_exact + artist_only_diagnostic",
        },
        "coverage": {
            **counts,
            "fma_development_artist_title_joinable": sum(
                by_split[s]["joinable_artist_title"] for s in SPLITS
            ),
            "mtg_catalog_metadata_rows": mtg_rows,
            "mtg_distinct_artist_title_pairs": len(mtg_pairs),
        },
        "by_split": {split: serial(by_split[split]) for split in SPLITS},
        "by_genre": {
            split: {genre: serial(genre_counts)
                    for genre, genre_counts in sorted(by_genre[split].items())}
            for split in SPLITS
        },
        "source_sha256": {
            "fma_metadata_archive_sha256": digest(fma_metadata_zip),
            "mtg_raw_meta_tsv_sha256": digest(mtg_metadata_tsv),
        },
        "limitations": [
            "Exact artist/title catalog matches are possible overlaps only; recording identity is not verified.",
            "Artist-only collisions are especially weak matches; no artist names, track titles or IDs are emitted.",
            "The MTG raw metadata catalog is not the ONNX model's exact training subset.",
            "No match is not evidence of training disjointness: recordings, spellings, metadata and encoders differ.",
            "FMA official TEST metadata identities/genre labels and TEST audio remain uninspected.",
            "This reports provenance and leakage risk only; no similarity metric quality is measured.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fma-metadata-zip", type=Path, required=True)
    p.add_argument("--mtg-metadata-tsv", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Research audit must never overwrite an existing report")
    for item in (args.fma_metadata_zip, args.mtg_metadata_tsv):
        if not item.is_file():
            p.error(f"Input missing: {item}")
    result = inspect(args.fma_metadata_zip, args.mtg_metadata_tsv)
    if (result["coverage"]["training"] != 6400
            or result["coverage"]["validation"] != 800
            or result["coverage"]["test_metadata_rows_not_inspected"] != 800):
        raise ValueError("Official FMA-Small split sizes changed; fail closed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": result["status"], "coverage": result["coverage"],
        "by_split": result["by_split"],
        "validation_by_genre": result["by_genre"]["validation"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
