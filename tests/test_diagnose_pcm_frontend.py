"""Unit tests for full precision Rust/native Mel comparison on shared PCM."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diagnose_pcm_frontend as diag


class ControlledPcmFrontendTests(unittest.TestCase):
    def test_precise_mel_equal_and_band_level_signal(self):
        count = diag.FRAMES_PER_PATCH + 3 * diag.PATCH_HOP
        rust = [[0.5] * 96 for _ in range(count)]
        native = [0.5] * (4 * 128 * 96)
        equal = diag.mel_errors(rust, native)
        self.assertEqual(equal["compared_coefficients"], 4 * 128 * 96)
        self.assertEqual(equal["maximum_absolute_error"], 0)
        self.assertEqual(equal["coefficients_over_0_001"], 0)
        # Two overlapping patches include the same shared global frame.
        index = ((2 * 128 + 16) * 96) + 23
        native[index] = 0.504
        d = diag.mel_errors(rust, native)
        self.assertAlmostEqual(d["maximum_absolute_error"], 0.004)
        self.assertEqual(d["coefficients_over_0_001"], 1)
        self.assertEqual(d["worst"]["patch"], 2)
        self.assertEqual(d["worst"]["global_frame"], 2 * 62 + 16)
        self.assertEqual(d["worst"]["mel_band"], 23)
        self.assertEqual(d["worst_bands_by_mean_error"][0], 23)

    def test_rejects_malformed_mel(self):
        frames = [[0.0] * 96 for _ in range(314)]
        native = [0.0] * (4 * 128 * 96)
        with self.assertRaisesRegex(AssertionError, "too few"):
            diag.mel_errors(frames[:313], native)
        with self.assertRaisesRegex(AssertionError, "shape mismatch"):
            diag.mel_errors(frames, native[:4])
        frames[10][0] = float("nan")
        with self.assertRaisesRegex(AssertionError, "Nonfinite Mel"):
            diag.mel_errors(frames, native)


if __name__ == "__main__":
    unittest.main()
