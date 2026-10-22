#!/usr/bin/env python3
"""Expose version-pinned CI-only ffmpeg AND ffprobe without Ubuntu multimedia APT."""
import os
from pathlib import Path
import subprocess

import imageio_ffmpeg
from ffprobe_binaries import get_ffprobe_path


def require_working_binary(binary: Path, name: str) -> str:
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"CI {name} is missing or not executable: {binary}")
    output = subprocess.run(
        [str(binary), "-hide_banner", "-version"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    if not output or not output[0].startswith(f"{name} version "):
        raise RuntimeError(f"Unexpected {name} version output from {binary}: {output[:1]}")
    return output[0]


def main() -> None:
    # imageio-ffmpeg's pinned platform wheel bundles FFmpeg but NOT ffprobe.
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    if ffmpeg.parent.name != "binaries":
        raise RuntimeError(f"Expected FFmpeg bundled in imageio-ffmpeg wheel, got {ffmpeg}")
    ffmpeg_version = require_working_binary(ffmpeg, "ffmpeg")
    encoders = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-encoders"],
        check=True, capture_output=True, text=True,
    ).stdout
    for name in ("libmp3lame", "flac"):
        if name not in encoders:
            raise RuntimeError(f"Bundled FFmpeg lacks required audio encoder: {name}")

    # This is the real ffprobe CLI used unchanged by src/audio_decode.rs.
    # Pin its wheel version as an independent CI dependency.
    ffprobe = Path(get_ffprobe_path()).resolve()
    ffprobe_version = require_working_binary(ffprobe, "ffprobe")

    cli_dir = Path(os.environ["RUNNER_TEMP"]) / "ci-ffmpeg-cli"
    cli_dir.mkdir(parents=True, exist_ok=True)
    for name, binary in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        link = cli_dir / name
        link.symlink_to(binary)
    with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as path_file:
        path_file.write(f"{cli_dir}\n")

    print(f"CI fixture encoder: {ffmpeg_version}")
    print(f"CI audio metadata probe: {ffprobe_version}")
    print(f"Added both commands to PATH for subsequent CI steps: {cli_dir}")


if __name__ == "__main__":
    main()
