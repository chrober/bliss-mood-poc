#!/usr/bin/env python3
"""Strictly paired MTT A/B: pooled 1280D audio cosine vs classifier baselines.

Research only. All 346 questions are exploratory and NOT a fresh holdout.
No clip IDs, votes, feature vectors or artists are written to the aggregate report.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import benchmark_magnatagatune as mtt
import evaluate_similarity as ev
from mtt_paired_evidence import paired_sensitivity
from fixed_rank_fusion import FIXED_FUSIONS, predict as fixed_rank_prediction
import global_pairwise_fusion as gf

METHODS = {
    "embedding_cosine": ("embedding", ev.cosine),
    "genre_cosine": ("genre", ev.cosine),
    "mood_cosine": ("moodtheme", ev.cosine),
    "genre_centered_cosine": ("genre", ev.centered_cosine),
    "mood_centered_cosine": ("moodtheme", ev.centered_cosine),
}


def filename_for_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"


def validate_embedding(data: dict, key: str, audio_sha: str, patches: int,
                       encoder_sha: str, preprocessing: str, fingerprint: str | None) -> tuple:
    expected = {
        "schema_version": 1, "kind": "discogs_effnet_song_embedding",
        "validation_status": "experimental_unvalidated", "dimension": 1280,
        "patches_analyzed": patches, "audio_sha256": audio_sha,
        "encoder_sha256": encoder_sha, "preprocessing_version": preprocessing,
        "pooling_version": "patch_f64_arithmetic_mean_v1",
        "normalization_version": "song_f64_l2_then_cast_f32_v1",
        "track_file": key,
    }
    for field, value in expected.items():
        if data.get(field) != value:
            raise ValueError(f"Incompatible embedding provenance: {field}")
    if not isinstance(data.get("representation_fingerprint"), str) or len(data["representation_fingerprint"]) != 64:
        raise ValueError("Missing embedding representation fingerprint")
    if fingerprint is not None and data["representation_fingerprint"] != fingerprint:
        raise ValueError("Mixed embedding encoder/pooling provenance")
    # Check a reproducible, explicit fingerprint contract, independently of Rust.
    contract = [1, data["encoder_model"], encoder_sha, preprocessing,
                data["pooling_version"], data["normalization_version"], 1280]
    actual_fp = hashlib.sha256(json.dumps(contract, ensure_ascii=False,
                                        separators=(",", ":")).encode()).hexdigest()
    if data["representation_fingerprint"] != actual_fp:
        raise ValueError("Embedding representation fingerprint mismatch")
    vector = data.get("vector_f32")
    if not isinstance(vector, list) or len(vector) != 1280:
        raise ValueError("Expected exactly 1280 embedding components")
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector):
        raise ValueError("Embedding contains nonfinite components")
    length = math.sqrt(sum(x*x for x in vector))
    if not abs(length - 1) < 1e-5:
        raise ValueError("Expected L2-normalized song embedding")
    return tuple(vector)


def odd_one_out(triple: tuple, vectors: dict, metric) -> tuple[str | None, str | None]:
    a, b, c = triple
    pair_scores = [
        metric(vectors[a], vectors[b]),
        metric(vectors[a], vectors[c]),
        metric(vectors[b], vectors[c]),
    ]
    if any(s is None or not math.isfinite(s) for s in pair_scores):
        return None, "undefined"
    best = max(pair_scores)
    if sum(abs(s - best) <= 1e-12 for s in pair_scores) != 1:
        return None, "tie"
    return (c, b, a)[pair_scores.index(best)], None


def evaluate(db: Path, embeddings: Path, comparisons: Path, clips: Path,
             *, fixed_rank_fusions: bool = False, global_pair_fusions: bool = False) -> dict:
    if mtt.digest(comparisons) != mtt.REGISTERED_MTT_COMPARISONS_SHA256:
        raise ValueError("MTT human comparisons provenance differs from pinned research metadata")
    if mtt.digest(clips) != mtt.REGISTERED_MTT_CLIPS_SHA256:
        raise ValueError("MTT clip catalog provenance differs from pinned research metadata")
    questions, catalog = mtt.triplets_by_vote(comparisons, clips)
    if len(questions) != 346:
        raise ValueError("Expected all 346 exploratory unique unordered MTT triplets")
    all_ids = sorted({id for triple in questions for id in triple})
    if len(all_ids) != 1019:
        raise ValueError("Expected all 1019 unique MTT clips")
    keys = {id: f"MTT/{id}.mp3" for id in all_ids}
    expected_names = {filename_for_key(key) for key in keys.values()}
    if not embeddings.is_dir() or {p.name for p in embeddings.iterdir()} != expected_names:
        raise ValueError("Missing or unexpected clip embedding export")
    with closing(ev.open_database(db)) as conn:
        cohorts = {head: ev._catalog(conn, head, experimental=True)
                   for head in ("genre", "moodtheme")}
        for head in cohorts:
            if cohorts[head]["preprocessing_version"] != (
                "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
            ):
                raise ValueError("Only corrected Rust-v5 MTT preprocessing is comparable")
        stored = ev.fetch_keys(conn, set(keys.values()), cohorts)
        vector_by_id = {}
        fingerprint = None
        encoder_sha = None
        for id in all_ids:
            key = keys[id]
            heads = stored.get(key, {})
            if set(heads) != {"genre", "moodtheme"}:
                raise ValueError("Incomplete classifier coverage for MTT clip")
            rows = conn.execute(
                """SELECT f.model_id, f.audio_sha256, f.patches_analyzed,
                          m.embedding_model, m.models_sha256_json
                   FROM feature_tracks f
                   JOIN feature_models m ON f.model_key=m.model_key
                   WHERE f.track_file=? ORDER BY f.model_id""", (key,)
            ).fetchall()
            if len(rows) != 2 or {r[0] for r in rows} != {"genre", "moodtheme"}:
                raise ValueError("Incomplete feature track provenance")
            audio_hashes = {row[1] for row in rows}
            patch_counts = {row[2] for row in rows}
            encoder_names = {row[3] for row in rows}
            if len(audio_hashes) != 1 or len(patch_counts) != 1 or len(encoder_names) != 1:
                raise ValueError("Inconsistent audio or encoder across heads")
            enc_hashes = {json.loads(row[4]).get(row[3]) for row in rows}
            if len(enc_hashes) != 1 or not next(iter(enc_hashes)):
                raise ValueError("Classifier encoder fingerprints conflict")
            enc_sha = next(iter(enc_hashes))
            if encoder_sha is None:
                encoder_sha = enc_sha
            if enc_sha != encoder_sha:
                raise ValueError("Mixed encoder SHA across MTT clips")
            with (embeddings / filename_for_key(key)).open("r", encoding="utf-8") as file:
                data = json.load(file)
            vec = validate_embedding(
                data, key, next(iter(audio_hashes)), next(iter(patch_counts)),
                enc_sha, cohorts["genre"]["preprocessing_version"], fingerprint,
            )
            fingerprint = data["representation_fingerprint"]
            vector_by_id[id] = {"embedding": vec, "genre": heads["genre"],
                                "moodtheme": heads["moodtheme"]}

    methods = (list(METHODS)
               + (list(FIXED_FUSIONS) if fixed_rank_fusions else [])
               + (list(gf.FUSIONS) if global_pair_fusions else []))
    counts = {m: {"correct": 0, "predicted": 0, "undefined": 0, "metric_ties": 0}
              for m in methods}
    paired_rows = []
    tied_human = 0
    for triple in sorted(questions):
        votes = questions[triple]["votes"]
        majority_votes = max(votes.values())
        if sum(x == majority_votes for x in votes.values()) != 1:
            tied_human += 1
            continue
        human_outlier = max(votes, key=votes.get)
        outcomes = {}
        for name in methods:
            if name in gf.FUSIONS:
                prediction, abstention = odd_one_out(
                    triple, {id: vector_by_id[id] for id in triple},
                    lambda a, b, method=name: gf.pair_score(a, b, method)
                )
            elif name in FIXED_FUSIONS:
                prediction, abstention = fixed_rank_prediction(
                    triple, vector_by_id, FIXED_FUSIONS[name]
                )
            else:
                representation, metric = METHODS[name]
                vectors = {id: vector_by_id[id][representation] for id in triple}
                prediction, abstention = odd_one_out(triple, vectors, metric)
            if abstention:
                counts[name]["undefined" if abstention == "undefined" else "metric_ties"] += 1
            else:
                counts[name]["predicted"] += 1
            hit = int(prediction is not None and prediction == human_outlier)
            counts[name]["correct"] += hit
            outcomes[name] = hit
        artists = sorted(set(catalog[id]["artist"] for id in triple))
        paired_rows.append({"outcomes": outcomes, "artists": artists})
    scorable = len(questions) - tied_human
    if scorable != len(paired_rows) or scorable != 293:
        raise ValueError("MTT human majority denominator changed")
    scores = {}
    for method, count in counts.items():
        if count["predicted"] + count["undefined"] + count["metric_ties"] != scorable:
            raise ValueError("Incomplete paired MTT prediction accounting")
        scores[method] = {
            **count,
            "human_scorable_questions": scorable,
            "prediction_coverage": count["predicted"] / scorable,
            "accuracy_with_abstentions_as_incorrect": count["correct"] / scorable,
            "conditional_accuracy_if_predicted":
                count["correct"] / count["predicted"] if count["predicted"] else None,
        }
    paired = paired_sensitivity(paired_rows, methods)
    paired["schema"] = ("mtt-global-pairwise-fusion-exploratory-sensitivity-v1"
                        if global_pair_fusions else
                        "mtt-fixed-rank-fusion-exploratory-sensitivity-v1"
                        if fixed_rank_fusions else
                        "mtt-audio-heads-paired-exploratory-sensitivity-v1")
    paired["limits"] = [
        x.replace("Twenty-one post-hoc method comparisons per head", "Multiple post-hoc A/B comparisons")
        for x in paired["limits"]
    ]
    return {
        "schema_version": 3 if global_pair_fusions else (2 if fixed_rank_fusions else 1),
        "representation_comparison": ("fixed_global_pair_fusions_with_unchanged_baselines"
                                       if global_pair_fusions else
                                       "fixed_equal_rank_fusions_with_audio_genre_mood_baselines"
                                      if fixed_rank_fusions else
                                      "audio_embedding_vs_genre_mood_heads"),
        "global_pairwise_fusions": gf.provenance() if global_pair_fusions else None,
        "fixed_rank_fusions": ({"triplet_local": True, "no_label_fit": True,
                                "per_head_metric": "cosine",
                                "score_calibration": "within_triplet_three_pair_midranks_v1",
                                "weights": "equal_included_representations",
                                "combinations": FIXED_FUSIONS}
                               if fixed_rank_fusions else None),
        "status": "EXPLORATORY_346_MTT_NO_UNSEEN_HOLDOUT",
        "total_unique_triplets": len(questions),
        "human_ties": tied_human,
        "human_scorable_triplets": scorable,
        "unique_clips": len(all_ids),
        "paired_same_audio_and_questions": True,
        "encoder_sha256": encoder_sha,
        "representation_fingerprint": fingerprint,
        "methods": scores,
        "paired_sensitivity": paired,
        "limitations": [
            "All 346 MTT triplets already explored; not an independent holdout.",
            "Shared clips/artists; iid triplet CI not a population confidence interval.",
            "Artist cooccurrence graph is one connected component; artist weights are stress tests, not valid independent clusters.",
            "Unverified Discogs/MTG training-set overlap; apparent improvements may reflect leakage.",
            "Only nearest pair in three-song human odd-one-out; not direct evidence about good playlist transitions.",
            "No fusion weights selected from these exploratory results.",
            "Triplet-local rank fusion is not a globally calibrated similarity score or a production playlist policy.",
            "Global pair scores use fixed affine range mapping, not head-distribution calibration. All results are exploratory and post-hoc.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--embeddings-dir", type=Path, required=True)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--global-pair-fusions", action="store_true",
                   help="Four predeclared global, fixed-weight, label-free pairwise fusion ablations")
    p.add_argument("--fixed-rank-fusions", action="store_true",
                   help="Exploratory four predeclared equal-weight local Borda fusions; NO tuning")
    args = p.parse_args()
    result = evaluate(args.db, args.embeddings_dir, args.comparisons, args.clips,
                      fixed_rank_fusions=args.fixed_rank_fusions,
                      global_pair_fusions=args.global_pair_fusions)
    with args.out.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, allow_nan=False, indent=2)
    print(json.dumps({"status": result["status"], "scores": result["methods"]}, indent=2))


if __name__ == "__main__":
    main()
