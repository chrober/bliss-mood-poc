"""WP2-P1 grouped Bliss triplet evaluation and legacy Mahalanobis reuse tests."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_personal_triplet_protocol as p
from research_grouped_split import grouped_triplet_partition


def research_data():
    triples = []
    features = {}
    metadata = {}
    for i in range(8):
        ids = [f"private/{i}/a", f"private/{i}/b", f"private/{i}/c"]
        triples.append(ids)
        for j, key in enumerate(ids):
            # a/b close; c far, all values finite.
            features[key] = [float(i) + (0.01 if j == 1 else 0.0
                                        if j == 0 else 4.0)] + [0.0]*22
            metadata[key] = {
                "artist_group": f"artist-{i}",
                "album_group": f"album-{i}",
                "recording_group": key,
            }
    return triples, features, metadata


def matrix(diagonal=1.0):
    values = []
    for i in range(23):
        for j in range(23):
            values.append(diagonal if i == j else 0.0)
    return {"m": {"v": 1, "dim": [23, 23], "data": values}}


class PersonalProtocolTests(unittest.TestCase):
    def test_grouped_heldout_baseline_without_any_training(self):
        triples, features, metadata = research_data()
        out = p.study(triples, features, metadata)
        self.assertEqual(out["baseline_raw_23d_euclidean"]["accuracy_including_ties_as_incorrect"], 1.0)
        self.assertEqual(out["train_triplets"]+out["holdout_triplets"], 8)
        self.assertIsNone(out["legacy_learned_matrix"])
        self.assertTrue(out["guarantees"]["source_bliss_feature_scale_not_calibrated"])
        s = json.dumps(out)
        self.assertNotIn("private/", s)
        self.assertNotIn("artist-1", s)

    def test_valid_legacy_identity_matrix_requires_explicit_train_only_provenance(self):
        triples, features, metadata = research_data()
        split = grouped_triplet_partition(triples, metadata)
        with self.assertRaisesRegex(ValueError, "trained on exact"):
            p.study(triples, features, metadata, legacy_matrix=matrix())
        out = p.study(
            triples, features, metadata, legacy_matrix=matrix(),
            declared_training_triplet_indices=split["train_triplet_indices"],
        )
        self.assertEqual(out["legacy_learned_matrix"]["correct"], out["holdout_triplets"])
        self.assertEqual(out["status"], "DESCRIPTIVE_LEGACY_MATRIX_NOT_INDEPENDENTLY_CERTIFIED")
        self.assertTrue(out["guarantees"]["legacy_model_training_artifact_hash_not_independently_verified"])

    def test_legacy_matrix_numerical_validation(self):
        mat = p.frozen_matrix(matrix())
        self.assertAlmostEqual(p.distance([0.0]*23,[3.0]+[0.0]*22,mat), 3.0)
        with self.assertRaisesRegex(ValueError, "23D features"):
            p.distance([1.0], [2.0], mat)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            p.distance([0.0]*23, [float("nan")]+[0.0]*22, mat)
        bad = matrix(-1.0)
        with self.assertRaisesRegex(ValueError, "positive semidefinite"):
            p.frozen_matrix(bad)
        asym = matrix()
        asym["m"]["data"][1] = 0.25
        with self.assertRaisesRegex(ValueError, "symmetric"):
            p.frozen_matrix(asym)
        with self.assertRaisesRegex(ValueError, "23D matrix"):
            p.frozen_matrix({"m": {"v": 1, "dim": [23,23], "data": []}})

    def test_existing_learner_full_survey_training_is_not_certified_holdout(self):
        triples, features, metadata = research_data()
        with self.assertRaisesRegex(ValueError, "trained on exact"):
            p.study(
                triples, features, metadata, legacy_matrix=matrix(),
                declared_training_triplet_indices=list(range(len(triples))),
            )

    def test_corrupt_or_missing_bliss_rejected(self):
        triples, features, metadata = research_data()
        features.pop(triples[0][0])
        with self.assertRaisesRegex(ValueError, "missing Bliss"):
            p.study(triples, features, metadata)
        triples, features, metadata = research_data()
        features[triples[1][1]][3] = float("inf")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            p.study(triples, features, metadata)

    def test_one_component_has_no_independent_holdout(self):
        triples, features, metadata = research_data()
        for v in metadata.values():
            v["artist_group"] = "one-shared-artist"
        with self.assertRaisesRegex(ValueError, "No independent"):
            p.study(triples, features, metadata)

if __name__ == "__main__":
    unittest.main()
