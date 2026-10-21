#!/usr/bin/env python3
"""Create a blinded, 12-pair local A/B/C listening instrument from the SAME 100 songs.

Only existing local schema-v3 87D/56D vectors and verified 1280D sidecars
are read. No ONNX inference, audio decoding, uploads, SQLite writes or
Lyrion queue changes. Model scores remain in a separate PRIVATE sealed audit.
Selection strata are sampling hypotheses, never ground-truth musical labels.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import random
import sqlite3
import sys

import audit_local_feature_readiness as readiness
import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import filename_for_key, validate_embedding

SAMPLE = 100
SEED = 20261021
PILOT_COUNT = 12
# Genre intentionally receives three opportunities: earlier pilot had
# zero HUMAN positives for Genre. These are NOT assumed human positives.
STRATA = (
    "genre_high", "mood_high", "embedding_high",
    "genre_over_embedding", "embedding_over_genre", "low_all",
)
QUOTAS = {
    "genre_high": 3, "mood_high": 2, "embedding_high": 2,
    "genre_over_embedding": 2, "embedding_over_genre": 2, "low_all": 1,
}
CSV_FIELDS = (
    "left", "right", "genre_similarity_1to5", "mood_energy_similarity_1to5",
    "timbre_similarity_1to5", "next_track_suitability_1to5",
    "confidence_1to3", "notes",
)


def read_previous_pairs(path: Path | None) -> set[frozenset[str]]:
    """Optional overlap screen against OLD human-reviewed pairs; never edit them."""
    if path is None:
        return set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        first = stream.read(2048)
        stream.seek(0)
        delimiter = ";" if first.splitlines()[0].count(";") > first.splitlines()[0].count(",") else ","
        reader = csv.DictReader(stream, delimiter=delimiter)
        if reader.fieldnames is None or not {"left", "right"}.issubset(reader.fieldnames):
            raise ValueError("Earlier review CSV must contain exact left/right column names")
        prior = set()
        for row in reader:
            left, right = row.get("left"), row.get("right")
            if not left or not right or left == right:
                raise ValueError("Earlier listening review contains invalid pair keys")
            prior.add(frozenset((left, right)))
    return prior


def load_cohort(db: Path, embeddings: Path) -> tuple[dict, dict]:
    """Fail closed before creating ANY review files: exact frozen same-song provenance."""
    if not embeddings.is_dir():
        raise FileNotFoundError("Existing 1280D private sidecar directory is required")
    with closing(ev.open_database(db)) as conn:
        heads = {head: ev._catalog(conn, head, experimental=True) for head in ev.MODELS}
        if {m["preprocessing_version"] for m in heads.values()} != {readiness.V5_PREPROCESSING}:
            raise ValueError("Both classifiers must use corrected experimental Rust-v5 preprocessing")
        sample = ev.load_sample(conn, heads, SAMPLE, SEED)
        if (sample["valid_total"] != SAMPLE or sample["sample_size"] != SAMPLE
                or sample["invalid"] != 0):
            raise ValueError("Expected exactly 100 valid shared song features, no exclusions")
        keys = sorted(sample["tracks"])
        expected = {filename_for_key(k) for k in keys}
        found = {p.name for p in embeddings.iterdir() if p.is_file()}
        if expected != found:
            raise ValueError("Embedding folder must contain exactly the frozen 100 named JSON sidecars")
        items = {}
        fingerprint = None
        for key in keys:
            proof = readiness.provenance(conn, key, heads)
            if proof is None:
                raise ValueError("Inconsistent per-song Genre/Mood audio and encoder provenance")
            audio_sha, patches, encoder_sha = proof
            data = json.loads((embeddings / filename_for_key(key)).read_text(encoding="utf-8"))
            vector = validate_embedding(
                data, key, audio_sha, patches, encoder_sha,
                readiness.V5_PREPROCESSING, fingerprint,
            )
            fingerprint = data["representation_fingerprint"]
            items[key] = {**sample["tracks"][key], "embedding": vector}
    return items, {"tracks": SAMPLE, "schema_version": 3,
                   "same_audio_and_encoder_provenance": True,
                   "embedding_fingerprint_consistent": True,
                   "head_validation": {name: meta["validated"] for name, meta in heads.items()},
                   "status": "experimental_research_only"}


def within_rank(vals: list[float], value: float) -> float:
    return bisect_right(vals, value) / len(vals)


def artist_hint(key: str) -> str:
    # This is a weak path-derived diversity hint, NOT trusted artist metadata.
    return key.split("/", 1)[0].casefold() if "/" in key else ""


def select_pilot(items: dict, excluded: set[frozenset[str]], *,
                 seed: int = SEED) -> tuple[list[dict], dict]:
    keys = sorted(items)
    if len(keys) != SAMPLE:
        raise ValueError("Expected the same 100-song comparison cohort")
    rows = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if frozenset((a, b)) in excluded:
                continue
            x, y = items[a], items[b]
            scores = {
                "genre_cosine": ev.cosine(x["genre"], y["genre"]),
                "genre_centered_cosine": ev.centered_cosine(x["genre"], y["genre"]),
                "mood_cosine": ev.cosine(x["moodtheme"], y["moodtheme"]),
                "mood_centered_cosine": ev.centered_cosine(x["moodtheme"], y["moodtheme"]),
                "embedding_cosine": ev.cosine(x["embedding"], y["embedding"]),
            }
            if any(s is None or not math.isfinite(s) for s in scores.values()):
                raise ValueError("Undefined similarity score in frozen comparison cohort")
            rows.append({"pair": (a, b), "scores": scores})
    if len(rows) < 12:
        raise ValueError("Too few independent comparisons after exclusion")
    ranked = {
        score: sorted(row["scores"][score] for row in rows)
        for score in ("genre_centered_cosine", "mood_centered_cosine", "embedding_cosine")
    }
    for row in rows:
        s = row["scores"]
        row["pct"] = {
            "genre": within_rank(ranked["genre_centered_cosine"], s["genre_centered_cosine"]),
            "mood": within_rank(ranked["mood_centered_cosine"], s["mood_centered_cosine"]),
            "embedding": within_rank(ranked["embedding_cosine"], s["embedding_cosine"]),
        }

    rng = random.Random(seed + 919)
    def merit(row: dict, category: str) -> float:
        p = row["pct"]
        if category == "genre_high":
            return p["genre"]
        if category == "mood_high":
            return p["mood"]
        if category == "embedding_high":
            return p["embedding"]
        if category == "genre_over_embedding":
            return p["genre"] - p["embedding"]
        if category == "embedding_over_genre":
            return p["embedding"] - p["genre"]
        return 3 - p["genre"] - p["mood"] - p["embedding"]

    # Score ties are deterministically randomized instead of favoring
    # alphabetically early artists. No model score goes to the reviewer.
    rankings = {}
    for category in STRATA:
        decorated = [(merit(row, category), rng.random(), row) for row in rows]
        rankings[category] = [
            row for _, _, row in sorted(decorated, key=lambda r: (-r[0], r[1]))
        ]
    selected, used_keys, used_pairs = [], set(), set()
    remaining = dict(QUOTAS)
    while len(selected) < PILOT_COUNT:
        changed = False
        for category in STRATA:
            if remaining[category] == 0:
                continue
            choice = None
            for artist_distinct in (True, False):
                for row in rankings[category]:
                    a, b = row["pair"]
                    if a in used_keys or b in used_keys or row["pair"] in used_pairs:
                        continue
                    if artist_distinct and artist_hint(a) and artist_hint(a) == artist_hint(b):
                        continue
                    choice = row
                    break
                if choice is not None:
                    break
            if choice is None:
                raise ValueError("Cannot select 12 pairs with 24 distinct song keys")
            a, b = choice["pair"]
            selected.append({"pair": (a, b), "stratum": category,
                             "scores": choice["scores"], "percentiles": choice["pct"]})
            used_keys.update((a, b))
            used_pairs.add(choice["pair"])
            remaining[category] -= 1
            changed = True
        if not changed:
            raise ValueError("No valid candidates remaining")
    rng.shuffle(selected)
    public, private = [], []
    for i, item in enumerate(selected, 1):
        a, b = item["pair"]
        if rng.getrandbits(1):
            a, b = b, a
        public.append({name: (a if name == "left" else b if name == "right" else "")
                       for name in CSV_FIELDS})
        private.append({
            "pair_number": i, "left": a, "right": b,
            "selection_stratum_not_human_label": item["stratum"],
            "similarity_scores_not_probabilities": item["scores"],
            "cohort_percentiles_not_probabilities": item["percentiles"],
        })
    return public, {
        "schema": "private_blinded_local_ab_pilot_selection_v1",
        "seed": seed,
        "n_song_keys": len(keys),
        "n_candidate_pairs_after_exclusions": len(rows),
        "n_review_pairs": len(public),
        "unique_review_songs": len(used_keys),
        "earlier_review_pairs_excluded": (SAMPLE*(SAMPLE-1)//2) - len(rows),
        "sampling_quotas": QUOTAS,
        "pairs_private_do_not_open_before_review": private,
        "note": "Untrained scores and percentile strata are selection proxies, NOT true positive genre/mood labels.",
    }


def create_pilot(db: Path, embeddings: Path, out: Path,
                 reviewed_csv: Path | None = None) -> dict:
    if out.exists():
        raise FileExistsError("Choose a new output directory; never overwrite prior human listening data")
    previous = read_previous_pairs(reviewed_csv)
    items, cohort_info = load_cohort(db, embeddings)
    public, private = select_pilot(items, previous)
    private["source_provenance"] = cohort_info
    out.mkdir(parents=True, exist_ok=False)
    with (out / "listening-pairs.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(public)
    with (out / "selection-audit-private.json").open("x", encoding="utf-8") as stream:
        json.dump(private, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {
        "status": "BLINDED_REVIEW_READY",
        "source_song_count": 100, "source_features": ["genre_87d", "mood_56d", "embedding_1280d"],
        "all_100_embeddings_verified_against_same_original_audio": True,
        "pilot_pairs": PILOT_COUNT,
        "unique_songs_in_pilot": 24,
        "earlier_review_pairs_excluded": private["earlier_review_pairs_excluded"],
        "all_human_rating_cells_blank": True,
        "sampling_strata_hidden_in_private_audit": True,
        "files": ["listening-pairs.csv", "selection-audit-private.json"],
        "no_music_or_sqlite_changes": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--embedding-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--exclude-reviewed", type=Path,
                        help="Optional previous local listening CSV with exact left/right keys")
    args = parser.parse_args()
    try:
        print(json.dumps(create_pilot(args.db, args.embedding_dir, args.out_dir,
                                      args.exclude_reviewed), ensure_ascii=False, indent=2))
    except (ValueError, OSError, sqlite3.DatabaseError, KeyError, TypeError) as error:
        parser.exit(2, f"Pilot selection failed; local inputs/outputs were not uploaded: {type(error).__name__}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
