#!/usr/bin/env python3
"""Offline split-0 MTG-Jamendo and exact Essentia Genre/Mood class audit.

Accept six official split TSVs and two upstream model JSONs, no audio.
Match class identity and artist/track split disjointness, with fail-closed
schema validations. Output aggregate counts, hashes, provenance caveats.
This does NOT prove what audio examples trained the released ONNX weights.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import time

HEADS = {"genre": 87, "moodtheme": 56}
SPLITS = ("train", "validation", "test")
SOURCE = "https://github.com/MTG/mtg-jamendo-dataset"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def scan(path: Path, head: str, split: str) -> tuple[dict, set[str], set[str], set[str]]:
    track_keys, artists, classes = set(), set(), Counter()
    row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration as e:
            raise ValueError("Empty MTG split TSV") from e
        if header[:6] != ["TRACK_ID", "ARTIST_ID", "ALBUM_ID", "PATH", "DURATION", "TAGS"]:
            raise ValueError(f"Unexpected MTG split TSV header: {head}/{split}")
        for row in reader:
            if not row:
                continue
            if len(row) < 6 or any(not v.strip() for v in row[:5]):
                raise ValueError(f"Missing MTG split row fields: {head}/{split}")
            ident, artist = row[0], row[1]
            if ident in track_keys:
                raise ValueError(f"Duplicate MTG track within {head}/{split}")
            tags = [t.strip() for t in row[5:] if t.strip()]
            if not tags or any(not t.startswith(("genre---" if head=="genre" else "mood/theme---"))
                               for t in tags):
                raise ValueError(f"Unexpected tag category or unlabeled {head}/{split}")
            if len(set(tags)) != len(tags):
                raise ValueError("Duplicate tag within MTG song")
            row_count += 1
            track_keys.add(ident)
            artists.add(artist)
            classes.update(tags)
    if row_count < 1:
        raise ValueError(f"MTG {head}/{split} contains no tracks")
    return ({
        "tracks": row_count,
        "distinct_artists": len(artists),
        "distinct_tags": len(classes),
        "tag_positive_counts": dict(sorted(classes.items())),
        "mean_labels_per_track": sum(classes.values()) / row_count,
        "sha256": sha256(path),
    }, track_keys, artists, set(classes))


def inspect(folder: Path, model_dir: Path) -> dict:
    started = time.monotonic()
    out = {"schema": "mtg-jamendo-split0-model-audit-v1",
           "source": SOURCE,
           "split": "split-0",
           "status": "split_and_class_fingerprints_only_NOT_verified_model_training_provenance",
           "heads": {}, "model_provenance": {}}
    for head, dims in HEADS.items():
        names = {"genre": "mtg_jamendo_genre-discogs-effnet-1.json",
                 "moodtheme": "mtg_jamendo_moodtheme-discogs-effnet-1.json"}
        model_file = model_dir / names[head]
        metadata = json.loads(model_file.read_text(encoding="utf-8"))
        expected_classes = metadata.get("classes")
        if (metadata.get("type") != "multi-label classifier" or
            not isinstance(expected_classes, list) or
            len(expected_classes) != dims or
            len(set(expected_classes)) != dims):
            raise ValueError(f"Essentia head class cardinality mismatch: {head}")
        model_classes = {
            ("genre---" if head == "genre" else "mood/theme---") + cls
            for cls in expected_classes
        }
        if len(model_classes) != dims:
            raise ValueError("Essentia head duplicate class tokens")
        per_split = {}
        track_sets, artist_sets, tags_in_splits = {}, {}, set()
        for split in SPLITS:
            path = folder / f"autotagging_{head}-{split}.tsv"
            stat, tracks, artists, tags = scan(path, head, split)
            if tags - model_classes:
                raise ValueError(f"Unexpected upstream tags outside model classes: {head}/{split}")
            per_split[split] = stat
            track_sets[split] = tracks
            artist_sets[split] = artists
            tags_in_splits |= tags
        if tags_in_splits != model_classes:
            raise ValueError(f"MTG model/split class vocabulary differs for {head}")
        artist_pairs, track_pairs = {}, {}
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
            key = left + "_vs_" + right
            artist_pairs[key] = len(artist_sets[left] & artist_sets[right])
            track_pairs[key] = len(track_sets[left] & track_sets[right])
        if any(track_pairs.values()):
            raise ValueError("Official MTG split contains duplicate track across groups")
        out["heads"][head] = {
            "class_count": dims, "splits": per_split,
            "distinct_tracks_union": len(set.union(*track_sets.values())),
            "artist_overlaps_between_splits": artist_pairs,
            "track_overlaps_between_splits": track_pairs,
        }
        out["model_provenance"][head] = {
            "model_name": metadata.get("name"),
            "reported_dataset": metadata.get("dataset", {}).get("name"),
            "reported_test_metrics": metadata.get("dataset", {}).get("metrics"),
            "reported_embedding_model": metadata.get("inference", {}).get("embedding_model", {}).get("model_name"),
            "head_metadata_sha256": sha256(model_file),
            "head_classes_sha256": hashlib.sha256(
                "\n".join(expected_classes).encode("utf-8")
            ).hexdigest(),
        }
    out["runtime"] = {"audit_wall_seconds": round(time.monotonic()-started, 3)}
    out["limitations"] = [
        "Published source classes and split tags checked, not predictions nor ROC/PR AUC reproduced.",
        "Published head test metrics are descriptive metadata and not new experimental scores.",
        "The exact training split(s), embedding model training sets and dataset/audio overlap are not proven.",
        "Uploader tag annotation can be noisy, sparse and not a direct human similarity ranking.",
        "Aggregate statistics only; individual audio, track IDs, artists, titles and vectors not exported.",
    ]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-dir", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.report.exists():
        p.error("Refuse to overwrite research report")
    result = inspect(args.split_dir, args.models_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": result["status"],
        "heads": {head: {"tracks": {s: d["tracks"] for s, d in h["splits"].items()},
                         "classes": h["class_count"],
                         "artist_overlap": h["artist_overlaps_between_splits"]}
                  for head, h in result["heads"].items()},
        "audit_wall_seconds": result["runtime"]["audit_wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
