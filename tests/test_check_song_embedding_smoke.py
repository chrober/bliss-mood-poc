"""Regression for worker output discovery in the 1280D embedding smoke.

Classification JSONs share a prefix with embedding JSONs and must not be
misidentified as embedding vectors.  No audio/models/Rust required.
"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_song_embedding_smoke import discover_process_embedding_outputs


class ProcessEmbeddingFileDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def make(self, name):
        (self.directory / name).write_text("{}", encoding="utf-8")

    def test_four_embeddings_and_four_classifier_reports_are_not_confused(self):
        # Exact regression fixture for failed Actions run 39621028716.
        for index in range(1, 5):
            self.make(f"process-worker-{index}.json")
            self.make(f"process-worker-heads-{index}.json")
        paths = discover_process_embedding_outputs(self.directory, required=True)
        self.assertEqual([p.name for p in paths],
                         [f"process-worker-{i}.json" for i in range(1, 5)])

    def test_missing_worker_fails_closed(self):
        for index in (1, 2, 4):
            self.make(f"process-worker-{index}.json")
            self.make(f"process-worker-heads-{index}.json")
        with self.assertRaisesRegex(AssertionError, r"workers 1[.][.]4"):
            discover_process_embedding_outputs(self.directory, required=True)

    def test_extra_numeric_embedding_worker_is_not_ignored(self):
        for index in range(1, 6):
            self.make(f"process-worker-{index}.json")
        with self.assertRaises(AssertionError):
            discover_process_embedding_outputs(self.directory, required=True)

    def test_require_worker_flag_rejects_absent_all(self):
        for index in range(1, 5):
            self.make(f"process-worker-heads-{index}.json")
        self.assertEqual(discover_process_embedding_outputs(self.directory), [])
        with self.assertRaises(AssertionError):
            discover_process_embedding_outputs(self.directory, required=True)

    def test_standalone_smoke_may_have_no_process_workers(self):
        self.assertEqual(discover_process_embedding_outputs(self.directory), [])


if __name__ == "__main__":
    unittest.main()
