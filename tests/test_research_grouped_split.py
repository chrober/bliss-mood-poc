"""Synthetic leakage-aware grouped split gates for WP2 and WP3."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_grouped_split as g


def songs(groups=5, size=3):
    return [
        {
            "track_id": f"opaque-{i}-{j}",
            "artist_group": f"artist-{i}",
            "album_group": f"album-{i}",
            "recording_group": f"recording-{i}-{j}",
        }
        for i in range(groups) for j in range(size)
    ]


class GroupSplitTests(unittest.TestCase):
    def test_no_artist_album_recording_leak_and_deterministic(self):
        rows = songs(6, 3)
        a = g.grouped_partition(rows, test_fraction=0.33, seed=20261029)
        self.assertEqual(a, g.grouped_partition(rows, test_fraction=0.33, seed=20261029))
        self.assertTrue(a.train and a.holdout)
        self.assertEqual(set(a.train) & set(a.holdout), set())
        for field in g.GROUP_KEYS:
            train = {rows[i][field] for i in a.train}
            held = {rows[i][field] for i in a.holdout}
            self.assertFalse(train & held)

    def test_album_cross_artist_connects_and_can_make_holdout_impossible(self):
        rows = songs(3, 3)
        # Albums link artists 0->1->2, so no genuine holdout exists.
        rows[3]["album_group"] = rows[0]["album_group"]
        rows[6]["album_group"] = rows[4]["album_group"]
        with self.assertRaisesRegex(ValueError, "No independent"):
            g.grouped_partition(rows)

    def test_concurrent_shared_recording_never_crosses_splits(self):
        rows = songs(5, 3)
        rows[3]["recording_group"] = rows[0]["recording_group"]
        a = g.grouped_partition(rows)
        idx = set(a.holdout)
        self.assertEqual(0 in idx, 3 in idx)

    def test_triplets_are_role_preserved_and_group_disjoint(self):
        rows = songs(6, 3)
        metadata = {r["track_id"]: {k:r[k] for k in g.GROUP_KEYS} for r in rows}
        trips = [[rows[i]["track_id"] for i in range(j*3, j*3+3)] for j in range(6)]
        # A duplicate similar pair with swap cannot sneak into holdout.
        trips.append([trips[0][1], trips[0][0], trips[0][2]])
        answer = g.grouped_triplet_partition(trips, metadata, test_fraction=0.25)
        self.assertEqual(answer["train_triplet_count"] +
                         answer["holdout_triplet_count"], len(trips))
        self.assertTrue(answer["no_shared_track_artist_album_recording_or_triplet_family"])
        self.assertEqual(set(answer["train_triplet_indices"]) &
                         set(answer["holdout_triplet_indices"]), set())
        train = {x for i in answer["train_triplet_indices"] for x in trips[i]}
        held = {x for i in answer["holdout_triplet_indices"] for x in trips[i]}
        self.assertFalse(train & held)
        self.assertEqual(0 in answer["train_triplet_indices"],
                         len(trips)-1 in answer["train_triplet_indices"])

    def test_repeated_cross_artist_training_triplets_can_destroy_holdout(self):
        rows = songs(3, 3)
        meta = {r["track_id"]:{k:r[k] for k in g.GROUP_KEYS} for r in rows}
        # Two triplets tie all artist groups together.
        trips = [
            [rows[0]["track_id"], rows[3]["track_id"], rows[6]["track_id"]],
            [rows[1]["track_id"], rows[4]["track_id"], rows[7]["track_id"]],
        ]
        with self.assertRaisesRegex(ValueError, "No independent"):
            g.grouped_triplet_partition(trips, meta)

    def test_malformed_inputs_fail_closed(self):
        rows = songs()
        with self.assertRaises(ValueError):
            g.grouped_partition(rows, test_fraction=1.0)
        with self.assertRaises(ValueError):
            g.grouped_partition(rows, test_fraction=0.0)
        with self.assertRaises(ValueError):
            g.grouped_partition(rows+[dict(rows[0])])
        with self.assertRaises(ValueError):
            g.grouped_partition(rows, triplet_edges=[
                [rows[0]["track_id"], rows[0]["track_id"], rows[1]["track_id"]]
            ])
        with self.assertRaises(ValueError):
            g.grouped_triplet_partition([["u", "v", "w"]]*2,{})
        with self.assertRaises(ValueError):
            g.grouped_partition([{**r, "artist_group":""} for r in rows])

if __name__ == "__main__":
    unittest.main()
