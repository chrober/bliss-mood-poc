#!/usr/bin/env python3
"""Audio-free feasibility audit for artist-disjoint MTT triplet holdout.

The 533 ordered comparisons represent only 346 unordered clip triplets.
Connecting all artists co-occurring in a triplet forms components that
CANNOT be split without artist leakage. Previously scored development
smoke artists are frozen into development, never put into a holdout.
No artist name, clip ID, per-triplet vote or membership manifest exported.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import time

from benchmark_magnatagatune import triplets_by_vote, dev_selection


class Components:
    def __init__(self):
        self.parent = {}

    def root(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.root(self.parent[item])
        return self.parent[item]

    def unite(self, a: str, b: str) -> None:
        x, y = self.root(a), self.root(b)
        if x != y:
            if x > y:
                x, y = y, x
            self.parent[y] = x


def audit(comparisons: Path, clipinfo: Path, seed: int = 20261021) -> dict:
    started = time.monotonic()
    triple_data, catalog = triplets_by_vote(comparisons, clipinfo)
    clusters = Components()
    unknown = 0
    for triple in triple_data:
        artists = sorted({catalog[clip]["artist"] for clip in triple})
        if any(not a for a in artists):
            unknown += 1
            continue
        for artist in artists:
            clusters.root(artist)
        for artist in artists[1:]:
            clusters.unite(artists[0], artist)

    question_counts = Counter()
    artist_counts = Counter()
    for artist in list(clusters.parent):
        artist_counts[clusters.root(artist)] += 1
    for triple in triple_data:
        artists = [catalog[clip]["artist"] for clip in triple]
        if any(not a for a in artists):
            continue
        roots = {clusters.root(a) for a in artists}
        if len(roots) != 1:
            raise ValueError("Artist graph split invariant violated")
        question_counts[next(iter(roots))] += 1

    try:
        prior_smoke = dev_selection(triple_data, catalog, 4, seed)
    except ValueError as e:
        raise ValueError("Cannot reproduce already-executed 4-triple smoke") from e
    forced_development_components = {
        clusters.root(catalog[clip]["artist"])
        for triple in prior_smoke for clip in triple
    }
    # Select artist-connected components for a frozen candidate test pool
    # close to 20% of the remaining unique questions. This uses only
    # graph structure, not any human similarity votes or model scores
    # apart from acknowledging the already-executed, label-selected smoke.
    eligible = sorted(
        ((root, n) for root, n in question_counts.items()
         if root not in forced_development_components),
        key=lambda x: (x[1], x[0])
    )
    total = sum(question_counts.values())
    target = round(total * .2)
    # Exact subset-sum over at most 346 questions: minimize difference
    # from 20% without exposing which private artist components chosen.
    paths = {0: ()}
    for idx, (_, n) in enumerate(eligible):
        for prev, selection in sorted(list(paths.items()), reverse=True):
            value = prev + n
            if value not in paths:
                paths[value] = selection + (idx,)
    nontrivial = [n for n in paths if 0 < n < total]
    holdout = min(nontrivial, key=lambda n: (abs(n-target), n)) if nontrivial else 0
    chosen_indices = paths[holdout]
    chosen_roots = {eligible[i][0] for i in chosen_indices}
    if forced_development_components & chosen_roots:
        raise ValueError("Previously used smoke artist group leaked to holdout")
    dev_questions = total - holdout
    held_artists = sum(artist_counts[r] for r in chosen_roots)
    forced_dev_questions = sum(question_counts[r]
                               for r in forced_development_components)
    deterministic_manifest = "\n".join(sorted(
        hashlib.sha256(
            ("reserved-artists-v1\0" + str(seed) + "\0" + root).encode("utf8")
        ).hexdigest() for root in chosen_roots
    ))
    return {
        "schema": "magnatagatune-artist-connected-holdout-feasibility-v1",
        "status": "artist_component_metadata_plan_only_NOT_locked_test_evidence",
        "seed": seed,
        "ordered_comparison_rows": sum(x["permutations"] for x in triple_data.values()),
        "unique_unordered_triplets": len(triple_data),
        "triplets_with_missing_artist": unknown,
        "artist_components": len(question_counts),
        "largest_component_triplets": max(question_counts.values(), default=0),
        "top_five_component_sizes": sorted(question_counts.values(), reverse=True)[:5],
        "forced_development": {
            "previous_smoke_triplets": 4,
            "artist_components": len(forced_development_components),
            "unique_triplets_sharing_smoke_artist_components": forced_dev_questions,
        },
        "holdout_candidate": {
            "target_fraction": .2,
            "possible_artist_disjoint_holdout": holdout > 0
              and unknown == 0 and dev_questions > 0,
            "heldout_unique_triplets": holdout,
            "heldout_fraction": holdout / total if total else 0,
            "development_unique_triplets": dev_questions,
            "heldout_artist_count": held_artists,
            "heldout_component_count": len(chosen_roots),
            "component_selection_sha256": hashlib.sha256(
                deterministic_manifest.encode("ascii")
            ).hexdigest(),
        },
        "runtime": {"wall_seconds": round(time.monotonic()-started, 3)},
        "limitations": [
            "Group components reflect artist strings in clip metadata; they are not audio fingerprints.",
            "A previously scored smoke already selected human high-consensus questions; its components are forced into development.",
            "The proposed holdout assignment is only a feasibility plan, not yet final preregistration.",
            "Dataset artist/track group differences and empty metadata may prevent rigorous independence.",
            "No music, track/artist IDs, per-song features or raw human choices exported.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparisons", type=Path, required=True)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Report already exists")
    result = audit(args.comparisons, args.clips, args.seed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "status": result["status"],
        "unique_triplets": result["unique_unordered_triplets"],
        "artist_components": result["artist_components"],
        "largest_component": result["largest_component_triplets"],
        "forced_dev": result["forced_development"],
        "holdout_candidate": result["holdout_candidate"],
        "wall_seconds": result["runtime"]["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
