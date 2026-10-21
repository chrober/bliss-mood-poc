#!/usr/bin/env python3
"""Freeze metadata-only MagnaTagATune artist-disjoint holdout feasibility.

No audio and no similarity scores. Published 533 rows must be aggregated
into 346 unordered clip triples before artist-group split assignment.
Two strategies are audited (not silently interchanged):
- connected-artist components: every artist co-occurring in a triplet
  belongs to the same component; usable without discarding cross-fold
  triplets, but a giant component may make holdout impossible;
- fixed artist SHA-256 partition with mixed-artist triples excluded,
  yielding genuinely artist-disjoint development/holdout questions.
This is *not* independent of Discogs/MTG-Jamendo training provenance.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import time

from benchmark_magnatagatune import triplets_by_vote, dev_selection

SEED = 20261021
SALT = "MTT-artist-holdout-v1|20261021|"


def artist_bucket(artist: str, cutoff: int = 128) -> str:
    if not artist:
        return "unknown"
    if not 0 <= cutoff <= 256:
        raise ValueError("Artist holdout cutoff must be within byte range")
    code = hashlib.sha256((SALT + artist).encode("utf-8")).digest()[0]
    return "holdout" if code < cutoff else "development"


def digest_triplets(triplets) -> str:
    h = hashlib.sha256()
    for triple in sorted(triplets):
        h.update((",".join(triple) + "\n").encode("ascii"))
    return h.hexdigest()


def evaluate_inputs(triplets: dict, catalog: dict) -> dict:
    """Audit an already-loaded set of votes; useful for pre-inference gates."""
    started = time.monotonic()
    parent = {}
    def find(artist):
        parent.setdefault(artist, artist)
        if parent[artist] != artist:
            parent[artist] = find(parent[artist])
        return parent[artist]
    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    artists_by_triple = {}
    unknown = set()
    partition = defaultdict(list)
    for triple in sorted(triplets):
        names = tuple(catalog[clip]["artist"] for clip in triple)
        artists_by_triple[triple] = names
        if not all(names):
            unknown.add(triple)
            partition["missing_artist"].append(triple)
            continue
        union(names[0], names[1])
        union(names[0], names[2])
        choices = {artist_bucket(name) for name in names}
        if len(choices) != 1:
            partition["mixed_excluded"].append(triple)
        else:
            partition[next(iter(choices))].append(triple)

    component_artists = defaultdict(set)
    for artist in parent:
        component_artists[find(artist)].add(artist)
    component_triples = defaultdict(list)
    for triple, artists in artists_by_triple.items():
        if triple in unknown:
            continue
        component_triples[find(artists[0])].append(triple)

    # Sensitivity to the artist reserve size, using metadata only.
    # These are *candidate plans*, not test-set scores. Their exact
    # expected query counts can be audited without running any model.
    candidate_splits = {}
    for cutoff in (51, 85, 128):
        counts = Counter()
        artists_in_split = defaultdict(set)
        for triple, names in artists_by_triple.items():
            if not all(names):
                counts["missing_artist"] += 1
                continue
            buckets = {artist_bucket(name, cutoff) for name in names}
            if len(buckets) != 1:
                counts["mixed_excluded"] += 1
            else:
                split = next(iter(buckets))
                counts[split] += 1
                artists_in_split[split].update(names)
        if artists_in_split["development"] & artists_in_split["holdout"]:
            raise ValueError("Candidate artist partition contamination")
        candidate_splits[str(cutoff)] = {
            "intended_holdout_artist_fraction": round(cutoff / 256, 5),
            "questions": {label: counts[label] for label in
                          ("development", "holdout", "mixed_excluded", "missing_artist")},
            "artists": {label: len(artists_in_split[label]) for label in
                        ("development", "holdout")},
            "status": "metadata_feasibility_only_NOT_tested_on_model_scores",
        }

    # Prior four-triplet audio smoke used the complete published pool.
    # It was expressly exploratory, but its artists must never be called
    # unexposed independent holdout after formal partition selection.
    smoke = dev_selection(triplets, catalog, count=4, seed=SEED)
    smoke_artists = {
        catalog[clip]["artist"] for group in smoke for clip in group
    }
    exposed_holdout = [
        triple for triple in partition["holdout"]
        if set(artists_by_triple[triple]) & smoke_artists
    ]
    untouched_holdout = [
        triple for triple in partition["holdout"]
        if not set(artists_by_triple[triple]) & smoke_artists
    ]
    graph_sizes = sorted((len(t) for t in component_triples.values()), reverse=True)
    artists_development = {a for a in parent if artist_bucket(a) == "development"}
    artists_holdout = {a for a in parent if artist_bucket(a) == "holdout"}
    if artists_development & artists_holdout:
        raise ValueError("Artist contamination across frozen partitions")
    for triple in partition["development"]:
        if not all(a in artists_development for a in artists_by_triple[triple]):
            raise ValueError("Development artist contamination")
    for triple in partition["holdout"]:
        if not all(a in artists_holdout for a in artists_by_triple[triple]):
            raise ValueError("Holdout artist contamination")
    return {
        "schema": "magnatagatune-frozen-artist-partition-audit-v1",
        "status": "metadata_partition_frozen_NO_audio_scoring",
        "unique_unordered_triplets": len(triplets),
        "original_comparison_rows": sum(t["permutations"] for t in triplets.values()),
        "artist_hash_policy": "sha256('MTT-artist-holdout-v1|20261021|'+normalized_artist)_byte0_less_than_128_is_holdout",
        "artist_hash_seed": SEED,
        "artist_partition_counts": {"development": len(artists_development),
                                    "holdout": len(artists_holdout)},
        "artist_disjoint_questions": {
            group: {"count": len(partition[group]),
                    "sorted_triplet_id_sha256": digest_triplets(partition[group])}
            for group in ("development", "holdout", "mixed_excluded", "missing_artist")
        },
        "candidate_artist_holdout_designs": candidate_splits,
        "prior_four_triplet_smoke_exposure": {
            "distinct_artists_previously_analyzed": len(smoke_artists),
            "holdout_triplets_touching_smoke_artists": len(exposed_holdout),
            "holdout_triplets_never_touched_by_smoke_artists": len(untouched_holdout),
            "untouched_holdout_question_id_sha256": digest_triplets(untouched_holdout),
        },
        "artist_component_graph": {
            "components": len(component_artists),
            "artists_in_largest_component": max(
                (len(x) for x in component_artists.values()), default=0
            ),
            "triplets_in_largest_component": graph_sizes[0] if graph_sizes else 0,
            "component_triplet_count_p50": statistics.median(graph_sizes) if graph_sizes else None,
            "components_with_one_triplet": sum(n == 1 for n in graph_sizes),
        },
        "source_hashes": {},
        "runtime": {"wall_seconds": round(time.monotonic()-started, 3)},
        "limitations": [
            "Only published comparison artist strings, not audio fingerprints or classifier training labels.",
            "Mixed-artist triples excluded to keep artist-disjoint development and holdout under simple hash partition.",
            "A connected-component split may be unusable if most triples form one giant component.",
            "No split was chosen by inspecting any model similarity scores.",
            "Triplet hashes contain no explicit clip IDs or individual vote metadata.",
            "The prior 4-triplet smoke did not enforce this newly frozen split and remains functionality-only.",
            "Any holdout questions sharing artists with the prior smoke are excluded from untouched independent testing.",
        ],
    }


def evaluate(comparison_csv: Path, clips_csv: Path) -> dict:
    triplets, catalog = triplets_by_vote(comparison_csv, clips_csv)
    result = evaluate_inputs(triplets, catalog)
    result["source_hashes"] = {
        "comparison_sha256": hashlib.sha256(comparison_csv.read_bytes()).hexdigest(),
        "clip_info_sha256": hashlib.sha256(clips_csv.read_bytes()).hexdigest(),
    }
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args=p.parse_args()
    if args.report.exists():
        p.error("Output report exists")
    output=evaluate(args.comparisons,args.clips)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open("x",encoding="utf-8") as handle:
        json.dump(output,handle,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps({
        "unique_triplets": output["unique_unordered_triplets"],
        "artist_disjoint_question_counts": {k: v["count"] for k,v in
                                           output["artist_disjoint_questions"].items()},
        "candidate_designs": {cutoff: stats["questions"]
                              for cutoff, stats in output["candidate_artist_holdout_designs"].items()},
        "prior_smoke_exposure": output["prior_four_triplet_smoke_exposure"],
        "artist_component_graph": output["artist_component_graph"],
        "seconds": output["runtime"]["wall_seconds"],
        "status": output["status"]
    },indent=2))


if __name__ == "__main__":
    main()
