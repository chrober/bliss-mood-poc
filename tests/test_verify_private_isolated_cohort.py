"""Deterministic data-free regression tests for the private parity cohort runner."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "private_cohort", SCRIPTS / "verify_private_isolated_cohort.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def example_report():
    heads = {
        head: {
            "capability": head, "output_type": "sigmoid", "aggregation": "mean",
            "embedding_model": "encoder.onnx", "classification_model": head + ".onnx",
            "models_sha256": {"encoder.onnx": "a" * 64, head + ".onnx": "b" * 64},
            "model_key": "c" * 64, "validated_against_essentia": False,
            "scores": {f"label_{i}": 0.125 for i in range(n)},
        }
        for head, n in mod.OFFICIAL_HEAD_SCORES.items()
    }
    return {
        "schema_version": 3, "preprocessing_version": "test",
        "aggregation": "mean", "audio_sha256": "0" * 64,
        "sample_rate": 16000, "patches_analyzed": 5, "threads": 1,
        "classifications": heads,
    }


def vector():
    return {"dimension": 1280, "patches_analyzed": 5,
            "audio_sha256": "0" * 64, "vector_f32": [1.0] + [0.0] * 1279}


class PrivateCohortTests(unittest.TestCase):
    def test_manifest_stops_at_limit_and_preserves_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("one.wav", "über, song.flac", "three.mp3"):
                (root / name).write_bytes(b"synthetic")
            manifest = root / "private.txt"
            manifest.write_text("# ignore\none.wav\nüber, song.flac\nthree.mp3\n", encoding="utf-8")
            paths = mod.load_manifest(manifest, None, 2)
            self.assertEqual([p.name for p in paths], ["one.wav", "über, song.flac"])
            self.assertEqual((root / "one.wav").read_bytes(), b"synthetic")

    def test_missing_and_duplicate_inputs_fail_without_disclosing_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.wav").write_bytes(b"fake")
            manifest = root / "private.txt"
            manifest.write_text("one.wav\n./one.wav\n")
            with self.assertRaisesRegex(ValueError, "Duplicate source at manifest line 2"):
                mod.load_manifest(manifest, None, 12)
            manifest.write_text("one.wav\nmissing.wav\n")
            with self.assertRaisesRegex(ValueError, "Missing source at manifest line 2"):
                mod.load_manifest(manifest, None, 12)
            with self.assertRaisesRegex(ValueError, "limit"):
                mod.load_manifest(manifest, None, 40)

    def test_comparator_uses_real_three_path_gate_and_all_145_1280_values(self):
        seen = []
        metadata = example_report()
        def fake(args, *, timeout_seconds):
            seen.append((args[1], timeout_seconds))
            if args[1] == "analyze-features":
                return metadata
            return {"report": metadata, "embedding": vector()}
        result = mod.check_song(
            Path("private.wav"), exe=Path("scanner"), models_dir=Path("models"),
            backend="rust", native_worker=None, max_patches=None,
            timeout_seconds=30, analyzer=fake,
        )
        self.assertEqual(result, (145, 5))
        self.assertEqual([x[0] for x in seen], [
            "analyze-features", "internal-isolated-analyze-features",
            "internal-direct-analyze-features",
        ])

    def test_embedding_drift_fails_bit_exact_gate(self):
        metadata = example_report()
        def fake(args, *, timeout_seconds):
            if args[1] == "analyze-features":
                return metadata
            result = {"report": metadata, "embedding": vector()}
            if args[1] == "internal-isolated-analyze-features":
                result["embedding"]["vector_f32"] = [0.0, 1.0] + [0.0] * 1278
            return result
        with self.assertRaisesRegex(ValueError, "embedding f32 mismatch"):
            mod.check_song(
                Path("private.wav"), exe=Path("scanner"), models_dir=Path("models"),
                backend="rust", native_worker=None, max_patches=None,
                timeout_seconds=30, analyzer=fake,
            )


if __name__ == "__main__":
    unittest.main()
