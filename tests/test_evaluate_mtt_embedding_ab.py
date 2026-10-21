"""Offline contract tests for exploratory A/B embedding/genre/mood MTT evaluation."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_mtt_embedding_ab as ab
import evaluate_similarity as ev


class EmbeddingABTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 64
        self.audio = "c" * 64
        self.key = "MTT/123.mp3"
        self.preprocessing = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
        vector = [0.0] * 1280
        vector[0] = 1.0
        self.data = {
            "schema_version": 1,
            "kind": "discogs_effnet_song_embedding",
            "validation_status": "experimental_unvalidated",
            "dimension": 1280,
            "patches_analyzed": 3,
            "audio_sha256": self.audio,
            "encoder_model": "discogs-effnet-bsdynamic-1.onnx",
            "encoder_sha256": self.sha,
            "preprocessing_version": self.preprocessing,
            "pooling_version": "patch_f64_arithmetic_mean_v1",
            "normalization_version": "song_f64_l2_then_cast_f32_v1",
            "track_file": self.key,
            "vector_f32": vector,
        }
        contract = [
            1, self.data["encoder_model"], self.sha, self.preprocessing,
            self.data["pooling_version"], self.data["normalization_version"], 1280,
        ]
        self.data["representation_fingerprint"] = hashlib.sha256(json.dumps(
            contract, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()

    def check(self, data=None, fingerprint=None):
        return ab.validate_embedding(
            self.data if data is None else data, self.key, self.audio, 3,
            self.sha, self.preprocessing, fingerprint,
        )

    def test_valid_export_and_deterministic_private_filename(self):
        vector = self.check()
        self.assertEqual(len(vector), 1280)
        self.assertAlmostEqual(sum(v*v for v in vector), 1.)
        self.assertEqual(ab.filename_for_key(self.key),
                         hashlib.sha256(self.key.encode()).hexdigest() + ".json")
        self.assertEqual(self.check(fingerprint=self.data["representation_fingerprint"]), vector)

    def test_reject_wrong_audio_encoder_hash_pooling_and_nan(self):
        for field, corrupt in (
            ("audio_sha256", "f" * 64),
            ("patches_analyzed", 2),
            ("preprocessing_version", "wrong frontend"),
            ("encoder_sha256", "0" * 64),
            ("pooling_version", "other_pooling"),
            ("track_file", "MTT/124.mp3"),
        ):
            bad = dict(self.data)
            bad[field] = corrupt
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(data=bad)
        bad = dict(self.data, vector_f32=[math.nan] + [0.] * 1279)
        with self.assertRaises(ValueError):
            self.check(data=bad)
        bad = dict(self.data, vector_f32=[0.] * 1280)
        with self.assertRaises(ValueError):
            self.check(data=bad)
        with self.assertRaises(ValueError):
            self.check(fingerprint="0" * 64)

    def test_odd_one_out_and_undefined_ties(self):
        v = {"a": (1., 0.), "b": (.95, .05), "c": (-1., 0.)}
        self.assertEqual(ab.odd_one_out(("a", "b", "c"), v, ev.cosine),
                         ("c", None))
        self.assertEqual(ab.odd_one_out(("a", "b", "c"),
                                        {x: (0., 0.) for x in v}, ev.cosine),
                         (None, "undefined"))
        self.assertEqual(ab.odd_one_out(("a", "b", "c"),
                                        {x: (1., 0.) for x in v}, ev.cosine),
                         (None, "tie"))


if __name__ == "__main__":
    unittest.main()
