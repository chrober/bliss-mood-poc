#!/usr/bin/env python3
"""Research-only artist-aware FMA-Small Genre Retrieval validation.

Do not tune on the official FMA test split here. The first real workflow
uses the VALIDATION split and a tiny balanced sample. Dataset audio,
artist/track identities and per-track embeddings remain runner-private;
only aggregate retrieval statistics are emitted as an artifact.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import zipfile

import evaluate_similarity as ev
from audit_deam_mtg_overlap import clean, load_mtg_metadata

FMA_SOURCE = "https://github.com/mdeff/fma"
AUDIO_NAME = re.compile(r"^(\d{6})\.mp3$", re.IGNORECASE)
CLASSES = 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_fma_small(metadata_zip: Path,
                   *, include_artist_title: bool = False) -> dict[str, dict]:
    """Read official FMA two-row tracks.csv header. Internal IDs never export."""
    with zipfile.ZipFile(metadata_zip) as archive:
        files = [p for p in archive.namelist() if Path(p).name == "tracks.csv"]
        if len(files) != 1:
            raise ValueError("Expected one FMA tracks.csv")
        with archive.open(files[0]) as stream:
            csv.field_size_limit(16 * 1024 * 1024)
            reader = csv.reader(io.TextIOWrapper(
                stream, encoding="utf-8-sig", newline=""
            ))
            groups = next(reader)
            names = next(reader)
            cols = {(a.strip().lower(), b.strip().lower()): i
                    for i, (a, b) in enumerate(zip(groups, names))}
            required = (("set", "subset"), ("set", "split"),
                        ("track", "genre_top"), ("artist", "id"))
            if any(k not in cols for k in required):
                raise ValueError("Missing official FMA-Small split/genre/artist columns")
            if include_artist_title and any(k not in cols for k in
                    (("track", "title"), ("artist", "name"))):
                raise ValueError("Filtered FMA validation requires artist.name and track.title")
            songs = {}
            for row in reader:
                if len(row) != len(groups) or row[cols[("set", "subset")]].strip() != "small":
                    continue
                try:
                    ident = int(row[0])
                except ValueError:
                    raise ValueError("Invalid FMA-Small track ID")
                if ident <= 0:
                    raise ValueError("Invalid FMA-Small track ID")
                key = f"{ident:06d}"
                if key in songs:
                    raise ValueError("Duplicate FMA-Small track ID")
                split = row[cols[("set", "split")]].strip().lower()
                if split == "test":
                    # Never inspect TEST genre, artist, title in discovery.
                    continue
                if split not in ("training", "validation"):
                    raise ValueError("Unknown FMA official split")
                genre = row[cols[("track", "genre_top")]].strip()
                artist = row[cols[("artist", "id")]].strip()
                if not genre or not artist:
                    raise ValueError("Missing FMA development genre or artist")
                songs[key] = {"genre": genre, "artist": artist, "split": split}
                if include_artist_title:
                    a = clean(row[cols[("artist", "name")]].strip())
                    t = clean(row[cols[("track", "title")]].strip())
                    songs[key]["artist_title"] = (
                        (a, t) if (a and t and a not in ("unknown","various artists")
                                    and t not in ("unknown","untitled")) else None
                    )
    if len(songs) < 8:
        raise ValueError("Too few FMA-Small metadata tracks")
    if len({song["genre"] for song in songs.values()}) != CLASSES:
        raise ValueError("Expected eight FMA-Small major genre classes")
    return songs


def screen_mtg_catalog_matches(songs: dict, mtg_tsv: Path,
                               split: str) -> tuple[set[str], dict]:
    """Screen before inference, not the specific ONNX model training set."""
    if split != "validation":
        raise ValueError("Only official FMA VALIDATION is eligible for exploratory screen")
    pairs, rows = load_mtg_metadata(mtg_tsv)
    eligible = {ident: song for ident,song in songs.items()
                if song["split"] == "validation"}
    if any("artist_title" not in song for song in eligible.values()):
        raise ValueError("FMA artist and title metadata not loaded")
    excluded = {ident for ident,song in eligible.items()
                if song["artist_title"] is not None and song["artist_title"] in pairs}
    joinable = sum(song["artist_title"] is not None for song in eligible.values())
    if len(eligible) != 800 or joinable < 750 or len(excluded) > 500:
        raise ValueError("Unexpected validation metadata screening coverage")
    return excluded, {
        "status": "partial_exact_artist_title_catalog_exclusion_NOT_verified_training_disjointness",
        "validation_total": len(eligible),
        "validation_joinable": joinable,
        "possible_catalog_matches_excluded": len(excluded),
        "validation_eligible_after_exclusion": len(eligible)-len(excluded),
        "mtg_catalog_rows": rows,
        "mtg_metadata_sha256": sha256_file(mtg_tsv),
        "caveats": [
            "Exact artist/title matches only suggest possible shared recordings.",
            "Nonmatches do not prove classifier or encoder training disjointness.",
            "The filtered and previous unfiltered validation cohorts are NOT paired.",
        ],
    }


def match_audio(audio_zip: Path, songs: dict) -> dict[str, str]:
    """Index canonical six-digit MP3 names; never extract entire 7.2-GiB ZIP."""
    members = {}
    invalid_sizes = 0
    with zipfile.ZipFile(audio_zip) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            match = AUDIO_NAME.fullmatch(Path(info.filename).name)
            if not match:
                continue
            ident = match.group(1)
            if ident not in songs:
                continue
            if ident in members:
                raise ValueError("Ambiguous MP3 filename for FMA track")
            if info.file_size < 10000 or info.file_size > 30 * 1024 * 1024:
                # Public FMA audio contains anomalous entries; exclude
                # them before deterministic sampling rather than failing
                # on an MP3 never used by the experiment.
                invalid_sizes += 1
                continue
            members[ident] = info.filename
    if invalid_sizes > 50:
        raise ValueError(
            f"Too many anomalous FMA MP3 archive members: {invalid_sizes}"
        )
    if len(members) < max(6, len(songs) - min(50, max(1, len(songs) // 100))):
        raise ValueError(
            f"Too few valid FMA MP3 files: {len(members)} of {len(songs)}"
        )
    print(f"FMA ZIP: {len(members)} usable MP3s, "
          f"{invalid_sizes} size anomalies excluded.", flush=True)
    return members


def balanced_sample(songs: dict, available: dict, split: str,
                    per_genre: int, seed: int) -> list[str]:
    if split not in ("training", "validation"):
        raise ValueError("Only non-test split allowed in discovery benchmark")
    if per_genre < 2 or per_genre > 100:
        raise ValueError("per_genre must be 2..100 for exploratory benchmark")
    buckets = defaultdict(list)
    for ident, item in songs.items():
        if ident in available and item["split"] == split:
            buckets[item["genre"]].append(ident)
    if len(buckets) != CLASSES:
        raise ValueError("Genre distribution incomplete in selected FMA split")
    rng = random.Random(seed)
    chosen, artists = [], set()
    for genre in sorted(buckets):
        pool = sorted(buckets[genre])
        rng.shuffle(pool)
        count = 0
        for ident in pool:
            artist = songs[ident]["artist"]
            if artist in artists:
                continue
            artists.add(artist)
            chosen.append(ident)
            count += 1
            if count == per_genre:
                break
        if count != per_genre:
            raise ValueError("Not enough independent artists for FMA genre " + genre)
    rng.shuffle(chosen)
    return chosen


def run_inference(binary: Path, models_dir: Path, archive_path: Path,
                  members: dict, chosen: list[str], database: Path) -> None:
    if database.exists():
        raise FileExistsError("Never overwrite existing feature database")
    database.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for index, ident in enumerate(chosen, 1):
            with tempfile.TemporaryDirectory(prefix="fma-validation-") as temp:
                source = Path(temp) / (ident + ".mp3")
                with archive.open(members[ident]) as data, source.open("wb") as output:
                    shutil.copyfileobj(data, output, length=1024 * 1024)
                completed = subprocess.run(
                    [str(binary.resolve()), "analyze-features", str(source),
                     "--models-dir", str(models_dir.resolve()),
                     "--models", "genre", "--threads", "1",
                     "--db", str(database.resolve()),
                     "--track-key", f"FMA/{ident}.mp3"],
                    check=False, capture_output=True, text=True, timeout=600
                )
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"FMA analysis failed for item {index}/{len(chosen)}: "
                        f"{completed.stderr[-2000:]}"
                    )
            print(f"Analyzed FMA item {index}/{len(chosen)}", flush=True)


def _retrieval(ranked: list[bool], all_relevant: int, k: int) -> tuple[float, float, float]:
    shown = ranked[:k]
    p_at_k = sum(shown) / k
    ap = (sum(sum(shown[:i]) / i for i, is_rel in enumerate(shown, 1)
              if is_rel) / min(k, all_relevant)) if all_relevant else 0.
    dcg = sum(1 / math.log2(rank + 1) for rank, is_rel in
              enumerate(shown, 1) if is_rel)
    ideal = sum(1 / math.log2(rank + 1)
                for rank in range(1, min(k, all_relevant) + 1))
    ndcg = dcg / ideal if ideal else 0.
    return p_at_k, ap, ndcg


def _bootstrap(values: list[float], seed: int, iterations: int = 400) -> list[float]:
    rng = random.Random(seed)
    n = len(values)
    sorted_means = sorted(
        statistics.fmean(values[rng.randrange(n)] for _ in range(n))
        for _ in range(iterations)
    )
    return [sorted_means[int(iterations * .025)],
            sorted_means[int(iterations * .975)]]


def evaluate(db: Path, chosen: list[str], songs: dict,
             seed: int, split: str) -> dict:
    keys = {ident: f"FMA/{ident}.mp3" for ident in chosen}
    with closing(ev.open_database(db)) as conn:
        cohort = ev._catalog(conn, "genre", experimental=True)
        if cohort["preprocessing_version"] != (
            "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
        ):
            raise ValueError("FMA evaluation requires verified Rust-v5 model cohort")
        vectors = ev.fetch_keys(conn, set(keys.values()), {"genre": cohort})
        if any("genre" not in vectors[keys[ident]] for ident in chosen):
            raise ValueError("Missing compatible Genre feature vectors")
        output = {}
        for metric, fn in ev.METRIC_FUNCS.items():
            p5, ap10, ndcg10 = [], [], []
            undefined = zero_abstained = incomplete = 0
            for anchor in chosen:
                candidates = [other for other in chosen if other != anchor
                              and songs[other]["artist"] != songs[anchor]["artist"]]
                positives = sum(songs[other]["genre"] == songs[anchor]["genre"]
                                for other in candidates)
                rankings = []
                for other in candidates:
                    score = fn(vectors[keys[anchor]]["genre"],
                               vectors[keys[other]]["genre"])
                    if score is None or not math.isfinite(score):
                        undefined += 1
                        continue
                    if (metric in ("topk_weighted_jaccard",
                                   "topk6_ranked_jaccard",
                                   "topk12_ranked_jaccard") and score <= 0):
                        # Zero overlap is an abstention, not a fabricated
                        # musical neighbor (no arbitrary filename tie break).
                        zero_abstained += 1
                        continue
                    rankings.append((score, other))
                if positives < 1 or len(rankings) < 10:
                    incomplete += 1
                    continue
                rankings.sort(key=lambda x: (-x[0], x[1]))
                judged = [songs[other]["genre"] == songs[anchor]["genre"]
                          for _, other in rankings]
                precision5, _, _ = _retrieval(judged, positives, 5)
                _, average_precision10, discounted10 = _retrieval(
                    judged, positives, 10
                )
                p5.append(precision5)
                ap10.append(average_precision10)
                ndcg10.append(discounted10)
            def describe(scores: list[float]) -> dict:
                return {
                    "query_count": len(scores),
                    "macro_mean": statistics.fmean(scores) if scores else None,
                    "query_bootstrap_95pct": _bootstrap(scores, seed)
                    if len(scores) >= 10 else None,
                }
            output[metric] = {
                "precision_at_5": describe(p5),
                "map_at_10": describe(ap10),
                "ndcg_at_10": describe(ndcg10),
                "queries_insufficient_candidates": incomplete,
                "candidate_pairs_undefined_score": undefined,
                "candidate_pairs_abstained_zero_overlap": zero_abstained,
            }
    # In this balanced, artist-unique sample, all queries have same prior:
    # (per_genre - 1) same-genre tracks among (N - 1) other tracks.
    per_genre = len(chosen) // CLASSES
    return {
        "schema": "fma-small-genre-retrieval-v1",
        "dataset": {
            "name": "FMA-Small", "source": FMA_SOURCE,
            "official_split": split, "sample_size": len(chosen),
            "genres_in_sample": {name: sum(songs[i]["genre"] == name
                                           for i in chosen)
                                  for name in sorted({songs[i]["genre"] for i in chosen})},
            "distinct_artists": len({songs[i]["artist"] for i in chosen}),
            "seed": seed, "sample_id_sha256": hashlib.sha256(
                ",".join(chosen).encode("ascii")
            ).hexdigest()
        },
        "genre_model": {
            "model_key": cohort["model_key"],
            "preprocessing_version": cohort["preprocessing_version"],
        },
        "baseline_random_precision_at_5": (per_genre - 1) / (len(chosen) - 1),
        "metric_results": output,
        "caveats": [
            "Coarse FMA top-level genre is a proxy for similarity, not direct pairwise music judgment.",
            "Official FMA test split remains untouched: validation-only exploratory scores.",
            "Same-artist candidates are excluded, and selected anchor artists are unique.",
            "Historical and ranked Top-K zero-overlap scores are abstentions, not random neighbors.",
            "Metric comparisons with different abstention coverage need common-query controls.",
            "Query-bootstrap intervals are descriptive and queries share candidate songs.",
            "No music, labels by track, artist identities or per-track features appear in the report.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metadata-zip", type=Path, required=True)
    p.add_argument("--audio-zip", type=Path, required=True)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--per-genre", type=int, default=10)
    p.add_argument("--split", choices=["validation", "training"], default="validation")
    p.add_argument("--seed", type=int, default=20261021)
    p.add_argument("--mtg-metadata-tsv", type=Path)
    p.add_argument("--exclude-mtg-catalog-matches", action="store_true")
    args = p.parse_args()
    if args.db.exists() or args.report.exists():
        p.error("Benchmark output exists; no overwrite permitted")
    for path in (args.metadata_zip, args.audio_zip, args.binary):
        if not path.is_file():
            p.error(f"Missing required benchmark input: {path}")
    if not args.models_dir.is_dir():
        p.error("Models directory does not exist")
    if args.exclude_mtg_catalog_matches and (
            args.split != "validation" or args.mtg_metadata_tsv is None
            or not args.mtg_metadata_tsv.is_file()):
        p.error("MTG catalog exclusion requires validation and --mtg-metadata-tsv")
    songs = load_fma_small(args.metadata_zip,
                          include_artist_title=args.exclude_mtg_catalog_matches)
    available = match_audio(args.audio_zip, songs)
    overlap = None
    if args.exclude_mtg_catalog_matches:
        excluded, overlap = screen_mtg_catalog_matches(
            songs, args.mtg_metadata_tsv, args.split
        )
        available = {ident: member for ident,member in available.items()
                     if ident not in excluded}
    chosen = balanced_sample(songs, available, args.split,
                             args.per_genre, args.seed)
    print(f"Matching FMA audio members: {len(available)}; "
          f"analyzing {len(chosen)} distinct-artist tracks, "
          f"{args.per_genre} per genre, split={args.split}.", flush=True)
    run_inference(args.binary, args.models_dir, args.audio_zip,
                  available, chosen, args.db)
    report = evaluate(args.db, chosen, songs, args.seed, args.split)
    report["dataset"]["metadata_zip_sha256"] = sha256_file(args.metadata_zip)
    report["dataset"]["audio_zip_sha256"] = sha256_file(args.audio_zip)
    report["catalog_overlap_exclusion"] = overlap or {
        "status": "NOT_PERFORMED_possible_MTG_catalog_overlap_not_removed"
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "dataset": report["dataset"]["name"],
        "split": report["dataset"]["official_split"],
        "songs": report["dataset"]["sample_size"],
        "random_p5": report["baseline_random_precision_at_5"],
        "cosine": report["metric_results"]["cosine"]["precision_at_5"],
    }, indent=2))


if __name__ == "__main__":
    main()
