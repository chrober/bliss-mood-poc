#!/usr/bin/env python3
"""Paired FMA-Small VALIDATION genre retrieval: 1280D audio vs 87D/56D heads.

Compares precisely the 80 catalog-screened, artist-distinct songs of the
previous FMA development study, using the SAME codec/encoder inference.
This is not an independent similarity ground truth or FMA official TEST.
Only aggregated results, never IDs, labels by track or vectors, are exported.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

import benchmark_fma_genre as fma
import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import validate_embedding, filename_for_key
from mtt_paired_evidence import quantile
import global_pairwise_fusion as gf

FROZEN_FMA80_SAMPLE_SHA256 = "f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509"
FROZEN_METADATA_SHA256 = "d9527a5297a65da31c5676484d5047c3e2b8a8060ce72a46e26158be736bf265"
FROZEN_AUDIO_SHA256 = "f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c"
FROZEN_MTG_SHA256 = "bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca"
# Frozen before the 1280D comparison: artifact from successful
# FMA screened-validation run 39606850307, not fitted to new embeddings.
FROZEN_ORIGINAL_GENRE_COSINE = {
    "precision_at_5": 0.32,
    "map_at_10": 0.17487599206349208,
    "ndcg_at_10": 0.29853323224865014,
}
PREPROCESSING = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
METHODS = {
    "embedding_cosine": ("embedding", ev.cosine),
    "genre_cosine": ("genre", ev.cosine),
    "genre_centered_cosine": ("genre", ev.centered_cosine),
    "mood_cosine": ("moodtheme", ev.cosine),
    "mood_centered_cosine": ("moodtheme", ev.centered_cosine),
}
MEASURES = ("precision_at_5", "map_at_10", "ndcg_at_10")


def digest_ids(chosen: list[str]) -> str:
    return hashlib.sha256(",".join(chosen).encode("ascii")).hexdigest()


def validate_study_scope(chosen: list[str], songs: dict, expected_sha256: str) -> None:
    if len(chosen) < 16 or len(chosen) % fma.CLASSES:
        raise ValueError("FMA same-query study requires balanced genre sample >= 16")
    if digest_ids(chosen) != expected_sha256:
        raise ValueError("FMA validation sample fingerprint changed: no valid A/B pairing")
    if len(set(chosen)) != len(chosen):
        raise ValueError("Duplicated song in FMA validation study")
    if any(songs[k]["split"] != "validation" for k in chosen):
        raise ValueError("FMA official TEST/TRAINING tracks forbidden in validation A/B")
    if len({songs[k]["artist"] for k in chosen}) != len(chosen):
        raise ValueError("FMA A/B requires independently selected artists")
    genre_counts = {genre: sum(songs[k]["genre"] == genre for k in chosen)
                    for genre in {songs[k]["genre"] for k in chosen}}
    if len(genre_counts) != fma.CLASSES or len(set(genre_counts.values())) != 1:
        raise ValueError("Expected equally represented FMA genres")


def load_vectors(db: Path, embedding_dir: Path, chosen: list[str]) -> tuple[dict, str, str]:
    keys = {ident: f"FMA/{ident}.mp3" for ident in chosen}
    required_names = {filename_for_key(key) for key in keys.values()}
    if not embedding_dir.is_dir() or {p.name for p in embedding_dir.iterdir()} != required_names:
        raise ValueError("Embedding directory must contain exactly the selected FMA cohort sidecars")
    with closing(ev.open_database(db)) as conn:
        cohorts = {head: ev._catalog(conn, head, experimental=True)
                   for head in ("genre", "moodtheme")}
        if any(meta["preprocessing_version"] != PREPROCESSING for meta in cohorts.values()):
            raise ValueError("FMA A/B requires corrected pinned Rust-v5 preprocessing")
        raw_vectors = ev.fetch_keys(conn, set(keys.values()), cohorts)
        vectors = {}
        fingerprint = None
        encoder_hash = None
        for ident in chosen:
            key = keys[ident]
            heads = raw_vectors.get(key, {})
            if set(heads) != set(cohorts):
                raise ValueError("FMA genre/mood coverage missing or invalid")
            metadata = conn.execute(
                """SELECT f.model_id, f.audio_sha256, f.patches_analyzed,
                          m.embedding_model, m.models_sha256_json
                   FROM feature_tracks f JOIN feature_models m ON f.model_key=m.model_key
                   WHERE f.track_file=? ORDER BY f.model_id""",
                (key,),
            ).fetchall()
            if len(metadata) != 2 or {row[0] for row in metadata} != set(cohorts):
                raise ValueError("Missing full feature provenance on FMA cohort")
            audio_hashes = {row[1] for row in metadata}
            patches = {row[2] for row in metadata}
            encoder_names = {row[3] for row in metadata}
            if len(audio_hashes) != 1 or len(patches) != 1 or len(encoder_names) != 1:
                raise ValueError("FMA encoder, audio SHA or patch count differs between heads")
            encoder_sha = {json.loads(row[4]).get(row[3]) for row in metadata}
            if len(encoder_sha) != 1 or not next(iter(encoder_sha)):
                raise ValueError("FMA model registry encoder fingerprint mismatch")
            sha = next(iter(encoder_sha))
            if encoder_hash is None:
                encoder_hash = sha
            if sha != encoder_hash:
                raise ValueError("Different encoder binaries in same FMA cohort")
            with (embedding_dir / filename_for_key(key)).open(encoding="utf-8") as file:
                blob = json.load(file)
            emb = validate_embedding(
                blob, key, next(iter(audio_hashes)), next(iter(patches)),
                sha, PREPROCESSING, fingerprint,
            )
            fingerprint = blob["representation_fingerprint"]
            vectors[ident] = {**heads, "embedding": emb}
    return vectors, encoder_hash, fingerprint


def evaluate_paired(vectors: dict, chosen: list[str], songs: dict,
                    *, seed: int, replicates: int = 800,
                    global_pair_fusions: bool = False) -> dict:
    """All anchors share identical 79 candidates and exactly 9 positives at n=80.

    Undefined method scores abstain for the ENTIRE query and earn 0; no method
    quietly gets a smaller/easier denominator. Tie handling matches the pinned
    preexisting FMA baseline (score desc, then stable opaque track ID).
    """
    if not 100 <= replicates <= 5000:
        raise ValueError("Replicates must be 100..5000")
    if set(vectors) != set(chosen):
        raise ValueError("All selected FMA tracks must have complete paired vectors")
    selected_methods = tuple(METHODS) + (tuple(gf.FUSIONS) if global_pair_fusions else ())
    results = {name: {measure: [] for measure in MEASURES} for name in selected_methods}
    diagnostics = {name: {"full_queries": 0, "abstained_queries": 0,
                          "candidate_scores_undefined": 0, "tied_pairs": 0}
                   for name in selected_methods}
    genre_indices = {}
    for index, anchor in enumerate(chosen):
        genre_indices.setdefault(songs[anchor]["genre"], []).append(index)
        candidates = [other for other in chosen
                      if other != anchor and songs[other]["artist"] != songs[anchor]["artist"]]
        positives = sum(songs[c]["genre"] == songs[anchor]["genre"] for c in candidates)
        if len(candidates) != len(chosen)-1 or positives != len(chosen)//fma.CLASSES-1:
            raise ValueError("FMA paired retrieval common-candidate policy violated")
        for name in selected_methods:
            ranked = []
            for other in candidates:
                if name in gf.FUSIONS:
                    score = gf.pair_score(vectors[anchor], vectors[other], name)
                else:
                    representation, fn = METHODS[name]
                    score = fn(vectors[anchor][representation],
                               vectors[other][representation])
                if score is None or not math.isfinite(score):
                    diagnostics[name]["candidate_scores_undefined"] += 1
                    continue
                ranked.append((score, other))
            if len(ranked) != len(candidates):
                diagnostics[name]["abstained_queries"] += 1
                for measure in MEASURES:
                    results[name][measure].append(0.0)
                continue
            diagnostics[name]["full_queries"] += 1
            ranked.sort(key=lambda row: (-row[0], row[1]))
            diagnostics[name]["tied_pairs"] += sum(
                ranked[i][0] == ranked[i-1][0] for i in range(1, len(ranked))
            )
            flags = [songs[c]["genre"] == songs[anchor]["genre"] for _, c in ranked]
            p5, _, _ = fma._retrieval(flags, positives, 5)
            _, ap10, ndcg10 = fma._retrieval(flags, positives, 10)
            for measure, value in zip(MEASURES, (p5, ap10, ndcg10)):
                results[name][measure].append(value)
    if len(genre_indices) != fma.CLASSES:
        raise ValueError("Genre-stratified resampling requires all eight genres")
    if any(len(scores[measure]) != len(chosen)
           for scores in results.values() for measure in MEASURES):
        raise ValueError("Paired query denominator inconsistent")

    # The same stratified resamples are used across methods AND metrics.
    # This is sensitivity to sampled queries, NOT an independent population CI:
    # retrieval queries share candidate tracks and genre labels.
    rng = random.Random(seed)
    resamples = [
        [rng.choice(indices) for _, indices in sorted(genre_indices.items())
         for _ in indices]
        for _ in range(replicates)
    ]
    report = {}
    for method, score in results.items():
        report[method] = {
            **diagnostics[method],
            "query_denominator": len(chosen),
            "query_coverage": diagnostics[method]["full_queries"] / len(chosen),
            **{measure: statistics.fmean(score[measure]) for measure in MEASURES},
        }
    paired = {}
    for baseline in (name for name in METHODS if name != "embedding_cosine"):
        paired[baseline] = {}
        for measure in MEASURES:
            deltas = [a-b for a,b in zip(results["embedding_cosine"][measure],
                                         results[baseline][measure])]
            draws = [statistics.fmean(deltas[i] for i in sample) for sample in resamples]
            paired[baseline][measure] = {
                "embedding_minus_baseline": statistics.fmean(deltas),
                "genre_stratified_shared_query_resampling_95pct_sensitivity":
                    [quantile(draws, .025), quantile(draws, .975)],
                "paired_queries": len(chosen),
            }
    return {
        "methods": report,
        **({"global_pairwise_fusions": gf.provenance()} if global_pair_fusions else {}),
        "paired_differences": paired,
        "genre_stratified_query_resampling": {
            "replicates": replicates, "seed": seed,
            "kind": "descriptive_query_sensitivity_NOT_independent_confidence_interval",
        },
        "candidate_policy": {
            "count_per_query": len(chosen)-1, "same_artist_excluded": True,
            "same_queries_and_candidates_for_all_methods": True,
            "undefined_candidate_score_abstains_whole_query": True,
            "abstention_on_common_denominator_is_zero": True,
            "tie_policy": "pinned_original_fma_score_desc_then_opaque_track_id",
        }
    }


def evaluate(db: Path, embedding_dir: Path, chosen: list[str], songs: dict,
             sample_sha256: str, *, seed: int = 20261021,
             replicates: int = 800, global_pair_fusions: bool = False) -> dict:
    validate_study_scope(chosen, songs, sample_sha256)
    vectors, encoder_sha, fingerprint = load_vectors(db, embedding_dir, chosen)
    outcomes = evaluate_paired(vectors, chosen, songs, seed=seed, replicates=replicates,
                               global_pair_fusions=global_pair_fusions)
    return {
        "schema": ("fma-catalog-screened-80-global-pair-fusion-exploratory-v2"
                   if global_pair_fusions else "fma-catalog-screened-80-embedding-vs-heads-v1"),
        "status": "FMA_VALIDATION_EXPLORATORY_NOT_INDEPENDENT_HOLDOUT",
        "dataset": "FMA-Small",
        "official_split": "validation",
        "sample_size": len(chosen),
        "distinct_artists": len({songs[ident]["artist"] for ident in chosen}),
        "sample_id_sha256": digest_ids(chosen),
        "encoder_sha256": encoder_sha,
        "representation_fingerprint": fingerprint,
        "random_precision_at_5": (len(chosen)//fma.CLASSES-1)/(len(chosen)-1),
        **outcomes,
        "limitations": [
            "FMA top-level genre is a coarse retrieval proxy, NOT human musical similarity judgment.",
            "Official FMA TEST untouched; results descriptive VALIDATION only.",
            "Possible exact MTG artist/title overlaps were excluded before frozen sample selection.",
            "Catalog nonmatches do not establish training disjointness for genre, mood or encoder models.",
            "80 artist-distinct queries share the same 80 candidate songs: query-bootstrap intervals are NOT independent population CIs.",
            "Mood agreement with genre labels is a negative/control proxy, not a Mood benchmark.",
            "No optimization or fusion weight selection from this already explored FMA VALIDATION cohort.",
            "No track identities, recording paths, per-track genres, artists, votes or vectors exported.",
        ]
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metadata-zip", type=Path, required=True)
    p.add_argument("--audio-zip", type=Path, required=True)
    p.add_argument("--mtg-metadata-tsv", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--embedding-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--global-pair-fusions", action="store_true",
                   help="Opt-in four predeclared no-training global pair-score ablations")
    p.add_argument("--original-genre-report", type=Path, required=True)
    p.add_argument("--selected-cache-manifest", type=Path,
                   help="Prove original FMA-Small archive SHA via checked selected-song manifest")
    args = p.parse_args()
    if args.out.exists():
        p.error("Never overwrite an existing aggregate research report")
    for name,path,sha in (
        ("FMA metadata",args.metadata_zip,FROZEN_METADATA_SHA256),
        ("MTG catalog",args.mtg_metadata_tsv,FROZEN_MTG_SHA256),
    ):
        if fma.sha256_file(path) != sha:
            raise ValueError(name + " publisher input SHA changed from registered FMA 80-song run")
    cached = None
    if args.selected_cache_manifest is not None:
        import fma_selected_audio_cache as fc
        cached = fc.verify(
            args.audio_zip,args.selected_cache_manifest,metadata=args.metadata_zip,
            mtg=args.mtg_metadata_tsv,screened=True,per_genre=10,seed=20261021
        )
        if cached["publisher_audio_zip_sha256"]!=FROZEN_AUDIO_SHA256:
            raise ValueError("FMA selected cache origin archive fingerprint mismatch")
    elif fma.sha256_file(args.audio_zip)!=FROZEN_AUDIO_SHA256:
        raise ValueError("Original full FMA source archive SHA changed")
    original = json.loads(args.original_genre_report.read_text(encoding="utf-8"))
    if (original["dataset"]["official_split"] != "validation"
            or original["dataset"]["sample_size"] != 80
            or original["dataset"]["seed"] != 20261021):
        raise ValueError("Only registered filtered FMA 80-song development cohort allowed")
    if original["catalog_overlap_exclusion"]["possible_catalog_matches_excluded"] != 42:
        raise ValueError("Changed FMA/MTG catalog screening result")
    songs = fma.load_fma_small(args.metadata_zip, include_artist_title=True)
    if cached is not None:
        chosen = cached["chosen"]
        available = {ident:cached["entries"][ident]["filename"] for ident in chosen}
    else:
        available = fma.match_audio(args.audio_zip, songs)
    excluded, audit = fma.screen_mtg_catalog_matches(songs,args.mtg_metadata_tsv,"validation")
    available = {ident: path for ident, path in available.items() if ident not in excluded}
    if cached is not None:
        if len(available)!=len(chosen):
            raise ValueError("Cached FMA selection overlaps rejected MTG catalog")
    else:
        chosen = fma.balanced_sample(songs, available, "validation", 10, 20261021)
    validate_study_scope(chosen, songs, FROZEN_FMA80_SAMPLE_SHA256)
    if digest_ids(chosen) != original["dataset"]["sample_id_sha256"]:
        raise ValueError("FMA A/B not paired with the existing genre-only run")
    output = evaluate(args.db,args.embedding_dir,chosen,songs,
                      FROZEN_FMA80_SAMPLE_SHA256,
                      global_pair_fusions=args.global_pair_fusions)
    for measure, reference in FROZEN_ORIGINAL_GENRE_COSINE.items():
        if (abs(output["methods"]["genre_cosine"][measure] -
                original["metric_results"]["cosine"][measure]["macro_mean"]) > 1e-9
                or abs(output["methods"]["genre_cosine"][measure] - reference) > 1e-9):
            raise ValueError(
                f"FMA paired genre baseline diverged from pre-embedding run: {measure}"
            )
    output["source_provenance_sha256"] = {
        "fma_metadata_zip": FROZEN_METADATA_SHA256,
        "fma_audio_zip": FROZEN_AUDIO_SHA256,
        "mtg_catalog": FROZEN_MTG_SHA256,
    }
    output["catalog_screening"] = {
        "possible_overlaps_excluded": audit["possible_catalog_matches_excluded"],
        "eligible_after_exclusion": audit["validation_eligible_after_exclusion"],
        "method": audit["status"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as dest:
        json.dump(output,dest,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({
        "status":output["status"],"n":output["sample_size"],
        "baseline_reproduced":True,"methods":output["methods"]
    },indent=2))


if __name__ == "__main__":
    main()
