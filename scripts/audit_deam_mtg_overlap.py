#!/usr/bin/env python3
"""Conservative metadata-only DEAM vs MTG-Jamendo overlap screening.

Matches exact normalized artist-and-title strings. A hit is a *possible*
recording/catalog overlap, not proof a recording was in a model's training
split. A non-hit does NOT prove absence of training overlap: identifiers,
recordings, spellings and releases differ. No audio, per-song IDs, names,
or metadata rows are emitted; only small aggregate research statistics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import zipfile

SOURCE = "https://cvml.unige.ch/databases/DEAM/"
MTG_SOURCE = "https://github.com/MTG/mtg-jamendo-dataset"
ARTIST_ALIASES = ("artist", "artist_name", "artistname")
DEAM_TITLE_ALIASES = ("song_title", "title", "track")
MTG_TITLE_ALIASES = ("track_name", "track_title", "title", "track")
DEAM_ID_ALIASES = ("song_id", "id")


def key_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def field(fields: dict, aliases: tuple[str, ...]) -> str | None:
    for name in aliases:
        if name in fields:
            return fields[name]
    return None


def clean(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    folded = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(re.findall(r"[\w]+", folded, flags=re.UNICODE))


def artist_title(row: dict, title_aliases: tuple[str, ...]) -> tuple[str, str] | None:
    normalized = {key_name(k): (v or "").strip()
                  for k, v in row.items() if k}
    artist = field(normalized, ARTIST_ALIASES)
    title = field(normalized, title_aliases)
    if not artist or not title:
        return None
    a, t = clean(artist), clean(title)
    if not a or not t:
        return None
    if a in ("unknown", "various artists") or t in ("unknown", "untitled"):
        return None
    return a, t


def load_deam_metadata(archive_path: Path) -> tuple[dict[str, tuple[str, str]], dict]:
    by_id: dict[str, tuple[str, str]] = {}
    conflicting: set[str] = set()
    invalid = 0
    files = []
    with zipfile.ZipFile(archive_path) as archive:
        for name in sorted(archive.namelist()):
            if not re.fullmatch(r"metadata_20(13|14|15)\.csv", Path(name).name, re.I):
                continue
            files.append(Path(name).name)
            with archive.open(name) as data:
                reader = csv.DictReader(io.TextIOWrapper(
                    data, encoding="utf-8-sig", errors="replace", newline=""
                ))
                if not reader.fieldnames:
                    raise ValueError("DEAM metadata CSV is empty")
                names = {key_name(n) for n in reader.fieldnames}
                if not (set(names) & set(DEAM_ID_ALIASES)) or "artist" not in names:
                    raise ValueError("DEAM metadata CSV lacks ID/artist fields")
                if not (set(names) & set(DEAM_TITLE_ALIASES)):
                    raise ValueError("DEAM metadata CSV lacks song title/track")
                for row in reader:
                    fields = {key_name(k): (v or "").strip()
                              for k, v in row.items() if k}
                    try:
                        ident = str(int(field(fields, DEAM_ID_ALIASES) or ""))
                    except (ValueError, TypeError):
                        invalid += 1
                        continue
                    if not 1 <= int(ident) <= 2058:
                        invalid += 1
                        continue
                    pair = artist_title(row, DEAM_TITLE_ALIASES)
                    if not pair:
                        invalid += 1
                        continue
                    if ident in by_id and by_id[ident] != pair:
                        conflicting.add(ident)
                    else:
                        by_id[ident] = pair
    if sorted(files) != ["metadata_2013.csv", "metadata_2014.csv", "metadata_2015.csv"]:
        raise ValueError("Expected DEAM metadata CSVs for 2013, 2014, and 2015")
    for ident in conflicting:
        by_id.pop(ident, None)
    if not by_id:
        raise ValueError("No joinable DEAM metadata rows")
    return by_id, {
        "deam_rows_with_valid_artist_title": len(by_id),
        "deam_ids_conflicting_metadata": len(conflicting),
        "deam_metadata_rows_invalid_or_generic": invalid,
        "deam_metadata_files": files,
    }


def load_mtg_metadata(tsv_path: Path) -> tuple[set[tuple[str, str]], int]:
    matched = set()
    rows = 0
    with tsv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("Empty MTG-Jamendo metadata")
        keys = {key_name(k) for k in reader.fieldnames}
        if not (set(keys) & set(ARTIST_ALIASES)):
            raise ValueError("MTG-Jamendo metadata lacks recognized artist column")
        if not (set(keys) & set(MTG_TITLE_ALIASES)):
            raise ValueError("MTG-Jamendo metadata lacks recognized title column")
        for row in reader:
            rows += 1
            pair = artist_title(row, MTG_TITLE_ALIASES)
            if pair:
                matched.add(pair)
    if rows < 1:
        raise ValueError("No MTG-Jamendo metadata records")
    return matched, rows


def check(deam_archive: Path, mtg_tsv: Path) -> dict:
    deam, stats = load_deam_metadata(deam_archive)
    mtg, mtg_rows = load_mtg_metadata(mtg_tsv)
    by_cohort = Counter()
    matches = Counter()
    for ident, pair in deam.items():
        cohort = "full_song_2015" if int(ident) >= 2001 else "earlier_excerpt"
        by_cohort[cohort] += 1
        if pair in mtg:
            matches[cohort] += 1
    def digest(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    return {
        "schema": "deam-mtg-exact-metadata-screen-v1",
        "deam_source": SOURCE,
        "mtg_source": MTG_SOURCE,
        "method": "normalized_NFKD_accent_fold_artist_plus_title_exact_match",
        "status": "partial_metadata_screen_only_NOT_verified_training_disjointness",
        "coverage": {**stats, "mtg_metadata_rows": mtg_rows,
                     "mtg_distinct_artist_title_pairs": len(mtg)},
        "by_cohort": {
            name: {"deam_metadata_joinable": by_cohort[name],
                   "mtg_catalog_exact_match_candidates": matches[name]}
            for name in ("earlier_excerpt", "full_song_2015")
        },
        "source_hashes": {
            "deam_metadata_zip_sha256": digest(deam_archive),
            "mtg_raw_metadata_tsv_sha256": digest(mtg_tsv),
        },
        "limitations": [
            "Positive match only means metadata coincide; not proof of audio identity or training usage.",
            "Non-match does NOT establish no training overlap: titles, artists, releases and recordings vary.",
            "MTG catalog is not the same as the specific MTG-Jamendo training split used by ONNX heads.",
            "Rows with unparseable or ambiguous metadata are omitted from exact matching.",
            "DEAM is not independent external test evidence until overlap and held-out controls are resolved.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deam-metadata-zip", type=Path, required=True)
    parser.add_argument("--mtg-metadata-tsv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for p in (args.deam_metadata_zip, args.mtg_metadata_tsv):
        if not p.is_file():
            parser.error(f"Missing input: {p}")
    if args.output.exists():
        parser.error("Output exists; never overwrite benchmark reports")
    result = check(args.deam_metadata_zip, args.mtg_metadata_tsv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as dest:
        json.dump(result, dest, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({"status": result["status"], "coverage": result["coverage"],
                      "by_cohort": result["by_cohort"]}, indent=2))


if __name__ == "__main__":
    main()
