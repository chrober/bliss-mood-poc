#!/usr/bin/env python3
"""Create CI-only synthetic files at the exact documented Windows launcher paths.

Never run this helper against a real user's local repository: it is intended
ONLY for ephemeral GitHub-hosted Windows CI runners; it refuses any existing
destination, detects CI, and uses 64 synthetic generated TracksV2 keys.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil

from test_run_local_bliss_essentia_teacher_study import LocalPairedStudyTests


def main() -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("RUNNER_OS") != "Windows":
        raise RuntimeError("Synthetic launcher fixtures are restricted to Windows GitHub Actions CI")
    root = Path(__file__).resolve().parents[1]
    bliss = root / "bliss.db"
    native = root / "benchmark-native-similarity-100-20261029" / "native-features.sqlite"
    if any(path.exists() or path.is_symlink() for path in (bliss,native)):
        raise RuntimeError("Refusing to replace existing source SQLite")
    source = LocalPairedStudyTests("test_real_source_adapters_aggregate_only_no_writes")
    source.setUp()
    try:
        native.parent.mkdir(exist_ok=False)
        shutil.copyfile(source.bliss,bliss)
        shutil.copyfile(source.essentia,native)
    finally:
        source.doCleanups()
    print("CI synthetic 64-song Bliss/Essentia paired fixture created; no real audio or track keys")


if __name__ == "__main__":
    main()
