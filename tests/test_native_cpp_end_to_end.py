"""Offline, no-model regression for native C++/Rust codec parity harness."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_native_cpp_end_to_end as parity


class NativeCppCodecParityTests(unittest.TestCase):
    def test_nonfinite_mismatch_is_rejected(self):
        # NaN comparisons must never be allowed to masquerade as parity.
        with self.assertRaises(AssertionError):
            parity.error_stats([0.0], [float("nan")], "nan")

    def test_small_differences_pass_with_complete_count(self):
        stats = parity.error_stats([0.5, 0.1, 0.0],
                                   [0.500001, 0.100003, 0.0], "test")
        self.assertEqual(stats["count"], 3)
        self.assertLess(stats["max_absolute_error"], 1e-3)

    def test_out_of_bounds_mismatch_fails(self):
        with self.assertRaises(AssertionError):
            parity.error_stats([0.1, 0.2], [0.102, 0.2], "test")

    def test_shortened_or_empty_arrays_fail_closed(self):
        for a, b in [([], []), ([0], []), ([1, 2], [1])]:
            with self.subTest(a=a, b=b):
                with self.assertRaises(AssertionError):
                    parity.error_stats(a, b, "length")

    def test_codec_matrix_is_complete(self):
        self.assertEqual(
            parity.AUDIO,
            ("mono-16k.wav", "stereo-44100.wav",
             "stereo-44100.flac", "stereo-44100.mp3")
        )


if __name__ == "__main__":
    unittest.main()
