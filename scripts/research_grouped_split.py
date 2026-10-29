#!/usr/bin/env python3
"""WP2-P1/WP3-R1: deterministic, group-disjoint partitions; no private I/O.

Groups share a partition if they share an artist, album, recording identity,
or a rated triplet. If this graph cannot produce a disjoint holdout, FAIL.
Never replace the split with a random track/triplet split.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Mapping, Sequence

GROUP_KEYS = ("artist_group", "album_group", "recording_group")


@dataclass(frozen=True)
class Partition:
    train: tuple[int, ...]
    holdout: tuple[int, ...]
    connected_groups: int
    achieved_holdout_fraction: float


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def _metadata_index(rows: Sequence[Mapping], keys: tuple[str, ...]) -> dict[str, int]:
    identity = {}
    for i, row in enumerate(rows):
        key = row.get("track_id")
        if not _valid_text(key) or key in identity:
            raise ValueError("Missing or duplicated opaque track identity")
        if any(not _valid_text(row.get(field)) for field in keys):
            raise ValueError("Track missing required private artist/album/recording group")
        identity[key] = i
    if len(identity) < 2:
        raise ValueError("At least two distinct tracks are required")
    return identity


def grouped_partition(
    rows: Sequence[Mapping], *, test_fraction: float = 0.25,
    seed: int = 20261029, triplet_edges: Sequence[Sequence[str]] = (),
    group_keys: tuple[str, ...] = GROUP_KEYS,
) -> Partition:
    """Hold out full connected components of shared identities and triplets.

    Returns only row indices, never the caller's private metadata or keys.
    Any heldout songs may have been encountered in an existing unrelated
    training dataset; this function cannot certify upstream model leakage.
    """
    if (type(test_fraction) is not float or not math.isfinite(test_fraction)
            or not 0 < test_fraction < 1):
        raise ValueError("test_fraction must be finite float strictly between 0 and 1")
    if type(seed) is not int or type(group_keys) is not tuple or not group_keys:
        raise ValueError("Invalid deterministic split configuration")
    if any(not _valid_text(field) for field in group_keys):
        raise ValueError("Invalid group-field contract")
    index = _metadata_index(rows, group_keys)
    parent = list(range(len(rows)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def unite(i: int, j: int) -> None:
        x, y = root(i), root(j)
        if x != y:
            parent[max(x, y)] = min(x, y)

    for group in group_keys:
        seen = {}
        for i, row in enumerate(rows):
            identity = row[group]
            if identity in seen:
                unite(seen[identity], i)
            else:
                seen[identity] = i

    for triple in triplet_edges:
        if len(triple) != 3 or len(set(triple)) != 3:
            raise ValueError("Malformed or repeated-member training triplet")
        if any(id not in index for id in triple):
            raise ValueError("Training triplet identity missing from metadata")
        anchor = index[triple[0]]
        unite(anchor, index[triple[1]])
        unite(anchor, index[triple[2]])

    components: dict[int, list[int]] = {}
    for i in range(len(rows)):
        components.setdefault(root(i), []).append(i)
    groups = list(components.values())
    if len(groups) < 2:
        raise ValueError("No independent artist/album/recording/triplet holdout exists")
    # Sort component sizes descending. Stable hash tie-break avoids relying on
    # input order or interpreter hash randomness. No identifiers are returned.
    groups.sort(key=lambda group: (
        -len(group),
        hashlib.sha256((str(seed)+"|"+",".join(sorted(
            rows[i]["track_id"] for i in group))).encode("utf-8")).hexdigest(),
    ))
    goal = len(rows) * test_fraction
    selected: list[list[int]] = []
    count = 0
    # Greedy target approximation, never split a connected component.
    # Leave at least one component in train.
    for component in groups:
        if len(selected) + 1 == len(groups):
            break
        next_count = count + len(component)
        if not selected or abs(next_count-goal) < abs(count-goal):
            selected.append(component)
            count = next_count
    if not selected or count == len(rows):
        raise ValueError("Cannot produce a nonempty disjoint holdout")
    held = frozenset(i for group in selected for i in group)
    train = tuple(i for i in range(len(rows)) if i not in held)
    test = tuple(i for i in range(len(rows)) if i in held)
    for field in group_keys:
        train_values = {rows[i][field] for i in train}
        test_values = {rows[i][field] for i in test}
        if train_values & test_values:
            raise AssertionError("Grouped holdout contains leakage")
    return Partition(train, test, len(groups), len(test)/len(rows))


def grouped_triplet_partition(
    triplets: Sequence[Sequence[str]],
    song_metadata: Mapping[str, Mapping], *,
    test_fraction: float = 0.25, seed: int = 20261029,
) -> dict:
    """Existing Bliss Lab order: [similar_1, similar_2, odd].

    Triplets touching shared songs OR artist/album/recording groups cannot
    cross between train and holdout. If this collapses everything into one
    component, refuse CV rather than fabricate independent validation.
    """
    if not isinstance(triplets, (list, tuple)) or len(triplets) < 2:
        raise ValueError("At least two labeled triplets are required")
    used = set()
    for triple in triplets:
        if (not isinstance(triple, (list, tuple)) or len(triple) != 3
                or any(not _valid_text(s) for s in triple)
                or len(set(triple)) != 3):
            raise ValueError("Malformed ordered Bliss triplet")
        used.update(triple)
    if any(key not in song_metadata for key in used):
        raise ValueError("Missing group metadata for rated track")
    rows = [dict(song_metadata[key], track_id=key) for key in sorted(used)]
    song_split = grouped_partition(
        rows, test_fraction=test_fraction, seed=seed, triplet_edges=triplets
    )
    train_songs = {rows[i]["track_id"] for i in song_split.train}
    held_songs = {rows[i]["track_id"] for i in song_split.holdout}
    train_ids, test_ids = [], []
    for j, triple in enumerate(triplets):
        group = set(triple)
        if group <= train_songs:
            train_ids.append(j)
        elif group <= held_songs:
            test_ids.append(j)
        else:
            raise AssertionError("A triplet crosses heldout song-group boundaries")
    if not train_ids or not test_ids:
        raise ValueError("No independent train/holdout triplet partition exists")
    return {
        "schema": "grouped_legacy_bliss_triplet_split_v1",
        "train_triplet_indices": tuple(train_ids),
        "holdout_triplet_indices": tuple(test_ids),
        "train_triplet_count": len(train_ids),
        "holdout_triplet_count": len(test_ids),
        "group_component_count": song_split.connected_groups,
        "no_shared_track_artist_album_recording_or_triplet_family": True,
        "upstream_essentia_teacher_train_overlap_not_certified": True,
    }
