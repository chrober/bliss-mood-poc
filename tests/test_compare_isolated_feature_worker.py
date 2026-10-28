"""Deterministic, data-free tests for the out-of-process inference parity gate."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "compare_isolated_feature_worker.py"
SPEC = importlib.util.spec_from_file_location("isolated_parity", SCRIPT)
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def report():
    def head(label, score):
        return {
            "capability": label, "output_type": "sigmoid",
            "aggregation": "arithmetic_mean_of_per_patch_sigmoid_scores",
            "embedding_model": "encoder.onnx", "classification_model": f"{label}.onnx",
            "models_sha256": {"encoder.onnx": "a" * 64, f"{label}.onnx": "b" * 64},
            "model_key": "c" * 64, "validated_against_essentia": False,
            "scores": {label: score},
        }
    return {
        "schema_version": 3, "preprocessing_version": "test-native",
        "aggregation": "arithmetic_mean_of_per_patch_sigmoid_scores",
        "audio_sha256": "0" * 64, "sample_rate": 16000,
        "patches_analyzed": 5, "threads": 1,
        "classifications": {
            "moodtheme": head("happy", 0.125),
            "genre": head("rock", 0.625),
            "voice": head("instrumental", 0.875),
        },
    }


class IsolatedParityTests(unittest.TestCase):
    def test_all_three_heads_and_identity_match(self):
        left = report()
        right = report()
        right["timings"] = {"total_seconds": 999.0}
        self.assertEqual(parity.compare_reports(left, right), (3, 3))

    def test_tiny_f32_score_difference_is_not_tolerated(self):
        left = report()
        right = report()
        right["classifications"]["genre"]["scores"]["rock"] = 0.626
        with self.assertRaisesRegex(ValueError, "f32 score mismatch"):
            parity.compare_reports(left, right)

    def test_model_fingerprint_drift_is_rejected(self):
        left = report()
        right = report()
        right["classifications"]["voice"]["model_key"] = "different"
        with self.assertRaisesRegex(ValueError, "model identity mismatch"):
            parity.compare_reports(left, right)

    def test_embedding_dimension_normalization_and_audio_identity(self):
        metadata = report()
        embedding = {
            "dimension": 1280, "vector_f32": [1.0] + [0.0] * 1279,
            "patches_analyzed": 5, "audio_sha256": "0" * 64,
        }
        parity.validate_embedding(embedding, metadata)
        embedding["vector_f32"][1] = float("nan")
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            parity.validate_embedding(embedding, metadata)

    def test_embedding_validation_is_not_mistaken_for_embedding_parity(self):
        metadata = report()
        embedding = {
            "dimension": 1280, "vector_f32": [1.0] + [0.0] * 1279,
            "patches_analyzed": 5, "audio_sha256": "1" * 64,
        }
        with self.assertRaisesRegex(ValueError, "audio hash"):
            parity.validate_embedding(embedding, metadata)


if __name__ == "__main__":
    unittest.main()
