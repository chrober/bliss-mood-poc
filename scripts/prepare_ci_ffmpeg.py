#!/usr/bin/env python3
"""Expose the pinned imageio-ffmpeg wheel's codec-capable FFmpeg as `ffmpeg` in CI."""
import os
from pathlib import Path
import subprocess

import imageio_ffmpeg


def main() -> None:
    binary = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    if binary.parent.name != "binaries" or not binary.is_file():
        raise RuntimeError(f"Expected FFmpeg bundled in imageio-ffmpeg wheel, got {binary}")
    version = subprocess.run(
        [str(binary), "-hide_banner", "-version"], check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()[0]
    encoders = subprocess.run(
        [str(binary), "-hide_banner", "-encoders"], check=True,
        capture_output=True, text=True,
    ).stdout
    for name in ("libmp3lame", "flac"):
        if name not in encoders:
            raise RuntimeError(f"Bundled FFmpeg lacks required audio encoder: {name}")
    cli_dir = Path(os.environ["RUNNER_TEMP"]) / "ci-ffmpeg-cli"
    cli_dir.mkdir(parents=True, exist_ok=True)
    cli = cli_dir / "ffmpeg"
    cli.symlink_to(binary)
    with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as path_file:
        path_file.write(f"{cli_dir}\n")
    print(f"CI fixture FFmpeg: {version}")
    print(f"Bundled executable: {binary}")
    print(f"Added to PATH for subsequent steps: {cli_dir}")


if __name__ == "__main__":
    main()
