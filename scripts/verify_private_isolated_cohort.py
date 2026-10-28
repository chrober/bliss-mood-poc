#!/usr/bin/env python3
"""Read-only exact direct/isolated ONNX comparison for a private local song cohort.

Never writes audio, SQLite, scores or embeddings; never prints song paths or
raw model outputs. The manifest and models stay on the user's computer.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

from compare_isolated_feature_worker import (
    OFFICIAL_HEAD_SCORES, compare_reports, compare_embeddings, run_analysis,
)

MAX_SONGS = 32


def load_manifest(manifest: Path, source_root: Path | None, limit: int) -> list[Path]:
    if not 1 <= limit <= MAX_SONGS:
        raise ValueError(f"Song limit must be within 1..={MAX_SONGS}")
    try:
        lines = manifest.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        raise ValueError("Cannot read local private manifest") from None
    root = source_root or manifest.parent
    songs: list[Path] = []
    seen: set[Path] = set()
    for line_number, raw in enumerate(lines, 1):
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        if "\0" in item:
            raise ValueError(f"Invalid input at manifest line {line_number}")
        selected = Path(item)
        if not selected.is_absolute():
            selected = root / selected
        if not selected.is_file():
            raise ValueError(f"Missing source at manifest line {line_number}")
        canonical = selected.resolve()
        if canonical in seen:
            raise ValueError(f"Duplicate source at manifest line {line_number}")
        songs.append(selected)
        seen.add(canonical)
        if len(songs) == limit:
            break
    if not songs:
        raise ValueError("Manifest selected no input tracks")
    return songs


def digest_file(path: Path) -> str:
    hashed = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def check_song(
    song: Path, *, exe: Path, models_dir: Path,
    backend: str, native_worker: Path | None, max_patches: int | None,
    timeout_seconds: int, analyzer=run_analysis,
) -> tuple[int, int]:
    common = [
        "--models-dir", str(models_dir), "--models", "moodtheme,genre,voice",
        "--audio-backend", backend, "--essentia-timeout-seconds", str(timeout_seconds),
    ]
    if native_worker:
        common.extend(["--essentia-worker", str(native_worker)])
    if max_patches is not None:
        common.extend(["--max-patches", str(max_patches)])
    binary = [str(exe)]
    public = analyzer(
        binary + ["analyze-features", str(song)] + common + ["--json"],
        timeout_seconds=timeout_seconds,
    )
    isolated = analyzer(
        binary + ["internal-isolated-analyze-features", str(song)]
        + common + ["--embedding", "--timeout-seconds", str(timeout_seconds)],
        timeout_seconds=timeout_seconds,
    )
    direct = analyzer(
        binary + ["internal-direct-analyze-features", str(song)]
        + common + ["--embedding"],
        timeout_seconds=timeout_seconds,
    )
    required = dict(expected_models=set(OFFICIAL_HEAD_SCORES),
                    expected_label_counts=OFFICIAL_HEAD_SCORES)
    heads, scores = compare_reports(public, isolated["report"], **required)
    compare_reports(public, direct["report"], **required)
    compare_reports(direct["report"], isolated["report"], **required)
    dimensions = compare_embeddings(
        direct["embedding"], isolated["embedding"], public,
    )
    if (heads, scores, dimensions) != (3, 145, 1280):
        raise ValueError("Required official model outputs are incomplete")
    return scores, public["patches_analyzed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--audio-backend", choices=["rust", "essentia"], default="rust")
    parser.add_argument("--essentia-worker", type=Path)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--max-patches", type=int,
                        help="Omit for a full-song, rather than partial-patch, check")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--expected-exe-sha256",
                        help="Optional exact SHA256 expected from the build artifact")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout_seconds <= 7200:
        parser.error("--timeout-seconds must be within 1..7200")
    if args.max_patches is not None and not 1 <= args.max_patches <= 2048:
        parser.error("--max-patches must be within 1..2048")
    if args.audio_backend == "essentia" and args.essentia_worker is None:
        parser.error("The essentia backend requires --essentia-worker")
    if not args.exe.is_file() or not args.models_dir.is_dir():
        parser.error("Executable and model directory must exist")
    if args.essentia_worker is not None and not args.essentia_worker.is_file():
        parser.error("The native Essentia worker must exist")
    if args.expected_exe_sha256 and not re.fullmatch(
        "[a-fA-F0-9]{64}", args.expected_exe_sha256
    ):
        parser.error("--expected-exe-sha256 must be a 64-digit hex SHA256")
    songs = load_manifest(args.manifest, args.source_root, args.limit)
    binary_hash = digest_file(args.exe)
    if args.expected_exe_sha256 and binary_hash != args.expected_exe_sha256.lower():
        raise ValueError("Executable SHA256 does not match the required build")
    for position, song in enumerate(songs, 1):
        try:
            check_song(
                song, exe=args.exe, models_dir=args.models_dir,
                backend=args.audio_backend, native_worker=args.essentia_worker,
                max_patches=args.max_patches, timeout_seconds=args.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Song position {position}: analyzer timeout") from None
        except (OSError, UnicodeError):
            raise RuntimeError(f"Song position {position}: analyzer I/O failure") from None
        except (ValueError, KeyError, TypeError, RuntimeError) as failure:
            raise RuntimeError(f"Song position {position}: {failure}") from None
    scope = "full-song" if args.max_patches is None else "first-patches-only"
    print(
        f"PASS: {len(songs)} read-only {scope} private inputs; "
        f"3 complete heads; 145 exact f32 scores/song; 1280 exact "
        f"embedding f32 components/song; executable_sha256={binary_hash}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError) as failure:
        print(f"FAIL: {failure}", file=sys.stderr)
        sys.exit(1)
