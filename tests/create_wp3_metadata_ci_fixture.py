#!/usr/bin/env python3
"""Write ONLY synthetic metadata SQLite under RUNNER_TEMP for GitHub Windows CI."""
from __future__ import annotations
import os
from pathlib import Path
import shutil

from test_derive_lyrion_research_groups import ResearchLyrionGroupsTests


def main() -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("RUNNER_OS") != "Windows":
        raise RuntimeError("This fixture is restricted to ephemeral Windows GitHub CI")
    root = Path(os.environ["RUNNER_TEMP"]) / "wp3-ci-metadata"
    if root.exists() or root.is_symlink():
        raise RuntimeError("Refusing to overwrite existing metadata fixtures")
    obj = ResearchLyrionGroupsTests("test_uses_real_snapshot_link_and_lms_album_ids_no_path_guess")
    obj.setUp()
    try:
        root.mkdir()
        shutil.copyfile(obj.library, root/"library.db")
        shutil.copyfile(obj.snapshot, root/"artist-repeat-identities.sqlite")
    finally:
        obj.doCleanups()
    print("Synthetic-only metadata fixtures created for Windows PowerShell validation")


if __name__ == "__main__":
    main()
