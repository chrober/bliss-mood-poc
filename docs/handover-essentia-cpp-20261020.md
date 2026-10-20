# Handover — Essentia C++ frontend / Rust orchestration (2026-10-20)

**Read this first in the next ChatGPT session.** This document captures the verified state of [draft PR #17](https://github.com/chrober/bliss-mood-poc/pull/17) before the handover-document commits, based on GitHub Actions **head `efda3f27e1965d65ebf73fad7de35bcba1dd907a`**. The docs commits themselves advance the PR head: always re-read the live PR and CI status before editing.

## Project, objective and non-negotiable decisions

- Repository: [`chrober/bliss-mood-poc`](https://github.com/chrober/bliss-mood-poc).
- Feature branch: **`feat/essentia-cpp-worker-backend`**; base branch: `main`. PR #17 **DRAFT; not merged**. Do not merge or modify `main` without explicit approval. Do not touch `lms-blissmixer-lab` in this workstream.
- Objective: **reuse the original upstream MTG/Essentia C++ implementation**, *not* `essentia-rs` and not a newly maintained Rust port of its DSP frontend.
- Keep the existing Rust scanner/worker scheduler, optional adaptive worker control, ONNX Runtime model inference, model registry, single SQLite sidecar writer and diagnostics.
- Keep the legacy **`--audio-backend rust` as the default**, with `--audio-backend essentia --essentia-worker <EXE>` explicit opt-in. No silent Rust fallback after a native worker error; no migration/production retagging.
- The library's own audio analysis and model classifications are still *experimental*; synthetic numerical parity does not establish subjective real-music labeling or relevance quality.

## Architecture (what actually runs)

~~~mermaid
flowchart TD
    L["bliss TracksV2 / audio sources (read-only)"] --> R["Rust scanner / optional adaptive worker orchestrator"]
    R --> W1["Rust worker 1: reusable ONNX sessions"]
    R --> WN["Rust worker N: reusable ONNX sessions"]
    W1 <-->|"EFW1/REQ1/RES1: file path ↔ Mel patches"| C1["Original Essentia C++ child process 1"]
    WN <-->|"Same IPC, independent process"| CN["Original Essentia C++ child process N"]
    C1 --> P["16 kHz mono / FrameCutter / TensorflowInputMusiCNN"]
    CN --> P
    W1 --> O["Discogs-EffNet 1280-d → 87 genre + 56 mood/theme + 2 voice"]
    WN --> O
    O --> DB["Single SQLite feature sidecar writer"]
~~~

Each Rust worker owns a long-lived, single-threaded original C++ subprocess, so no cross-thread Essentia object sharing is assumed. The Rust process owns lifecycle, deadlines, bounded in-flight work, child PID/memory observations, model sessions and persistence.

Key implementation:
- `native/essentia_cpp_worker.cpp` — original C++ Essentia `MonoLoader`, `FrameCutter`, `TensorflowInputMusiCNN` behind framed binary protocol. **No TensorFlow execution in C++ child.**
- `native/CMakeLists.txt` — C++ worker and separate protocol fixture; links via `pkg_check_modules(ESSENTIA ... essentia)`.
- `src/essentia_worker.rs` — Rust IPC subprocess reuse/restart/deadline; Windows signed deployment manifest validation and distinct backend fingerprint.
- `src/audio_decode.rs`, `src/preprocess.rs` — current Rust-reference decoder/DSP; keep available for parity and Rust backend.
- `src/features.rs` — ONNX EffNet and 3 classification heads, feature fingerprints and backend selection.
- `src/resources.rs` — process-tree RAM/PID metrics; relevant for multiworker comparisons.
- `scripts/test_native_essentia_protocol.py`, `scripts/compare_native_cpp_end_to_end.py` — real C++ protocol and numerical regression.
- `scripts/package_essentia_worker_windows.py` — recursively resolves Windows PE DLL imports, verifies hashes and writes `worker-dependencies.json`; **not a native compiler**.
- `scripts/benchmark_audio_backends.py` — paired fixed 1/2/4/6-worker Rust-vs-C++ scans, fresh SQLite sidecars, numerical-score consistency; needs bounded local real-audio cohort.
- Relevant CI: `.github/workflows/native-essentia-cpp.yml` (Linux original upstream), `.github/workflows/native-essentia-windows.yml` (Windows *original* C++), `.github/workflows/windows-native-packaging.yml` (**synthetic** Windows PE/DLL packaging), and existing Rust/Windows/Genre/Voice workflows.

## Verified status as of 2026-10-20, before this handover commit

| Gate | Result | Evidence |
| --- | --- | --- |
| Rust checks / Windows Rust executable | **PASS** | PR #17 head `efda3f27...` CI |
| Genre and voice model-reference parity | **PASS** | Same PR head |
| Windows native subprocess and DLL packaging with real dependent **fixture DLL** | **PASS**, but **synthetic**, not original Essentia | [Windows packaging run 39377836160](https://github.com/chrober/bliss-mood-poc/actions/runs/39377836160) |
| Linux **original Essentia C++** native worker (pinned older upstream), WAV/FLAC/MP3 Mel, EffNet 1280-d, 87/56/2 heads | **PASS** on deterministic synthetic audio | [Original C++ / ONNX parity run 39373185587](https://github.com/chrober/bliss-mood-poc/actions/runs/39373185587) |
| Windows **original upstream Essentia C++ library** built via MinGW64 Waf | **PASS: compilation and DLL linking completed** | [Windows run 39382026896](https://github.com/chrober/bliss-mood-poc/actions/runs/39382026896), upstream step successful |
| Windows **original Essentia C++ worker EXE** link | **FAIL: unresolved Essentia C++ symbols** | Same [run 39382026896](https://github.com/chrober/bliss-mood-poc/actions/runs/39382026896) |
| Actual Windows original-worker audio smoke and closed-DLL bundle | **NOT RUN**: dependent on link fix | Windows CI skipped these steps |
| Actual library A/B 1/2/4/6-worker performance | **NOT RUN** (harness ready) | Local bounded `TracksV2` + music required |
| ARM64/piCorePlayer packaging and validation, licensing audit | **OPEN** | Not production-ready |

**Exactly 7 of 8 checks passed** for head `efda3f27e196...`; the failing gate was **`Native original Essentia C++ Windows x64 (experimental)`**. GitHub job built `build/src/essentia.dll`, installed upstream via `waf install`, and CMake found `essentia` version `2.1-beta6-dev`. The worker object compiled; **final linkage** failed with undefined references, e.g.:

- `essentia::init()` and `essentia::shutdown()`
- `essentia::Logger::debug(...)` and `essentia::ParameterMap::add(...)`
- `essentia::nameOfType[abi:cxx11](...)`, `essentia::loggerInstance`, `essentia::debugIndentLevel`, `essentia::activatedDebugLevels`

This is a **symbol export/import/link configuration issue to investigate**, *not yet a proven root cause*. A successfully created DLL does **not** establish it exported the symbols required by a separate EXE; check both export table and actual CMake linker line before changing source. Read **[focused Windows linker handover](handover-essentia-windows-linker-20261020.md)** for commands and decision tree.

### Upstream version differences (do not conflate)

- **Linux proven reference:** upstream `MTG/essentia` at `9ceef0a3a7900ad51eb42aa5b6c6789b4bec6a47`, Ubuntu 22.04 / FFmpeg 4.4.
- **Windows trial:** upstream `MTG/essentia` at `b0661db99be4a8e2c6fabbe90a996f89786fdd8e` (unmerged upstream PR #1540, supporting FFmpeg 8/9, fetched with `refs/pull/1540/head` and SHA verified), MSYS2 MINGW64 / FFmpeg 9.0.2.
- Windows Waf: `--std=gnu++14 --lightweight=libav,libsamplerate,fftw` to avoid C++17 `std::byte` collisions and irrelevant TagLib/YAML/Chromaprint dependencies. CMake worker similarly sets GNU/MinGW C++14.
- These two upstream releases have **NOT** been numerically proven equivalent. A green Linux run does not clear the new Windows build.

## Next engineering steps, strictly ordered

1. **Inspect Windows library symbol exports and import library** and the `pkg-config`/CMake verbose link command for the generated C++ worker. Determine whether exports are absent, import libraries are absent/empty, or linkage targets the wrong artifact or ABI. Do not presume one explanation.
2. Fix **link/export mechanics only**, favoring build-system flags or an upstream-supported static/shared configuration; avoid forking Essentia DSP algorithms. Add explicit CI diagnostics/checks for symbols and exact linked binary provenance.
3. Obtain a **genuine original-Essentia-linked Windows EXE**, and pass its `EFW1` handshake plus multiple synthetic WAV/FLAC/MP3 requests and child reuse/restart tests.
4. Package the real DLL-closed worker, verify PE import closure, binary hashes and isolated process start. Keep artifacts non-redistributable pending dependency/AGPL license review.
5. Re-run **Windows original Essentia C++ vs production Rust** Mel-patch parity, 1280-d EffNet and 87/56/2 classes with the previously defined codec tolerances. Do not use the fixture-only gate as proof.
6. Only then run actual repeated 1/2/4/6-worker A/B comparisons on the same bounded Bliss cohort with fresh SQLite sidecars, read-only sources and process-tree RAM observability.
7. ARM64/piCorePlayer build/parity, upstream version and license audit before release decisions.

## Existing documentation / workflows to read

- [C++ subprocess/orchestrator architecture](essentia-cpp-worker-architecture.md) — includes Mermaid IPC and worker diagrams, provenance and parity.
- [Immediate Windows linker runbook](handover-essentia-windows-linker-20261020.md) — **next task**.
- [Windows native build trial](essentia-cpp-windows-native-build.md) — note newer verified status in this handover.
- [Windows DLL packaging and licensing](essentia-cpp-windows-packaging.md).
- [Paired audio backend benchmark](essentia-cpp-worker-benchmark.md).
- [Baseline adaptive-worker diagnostics](adaptive-scan-performance-handover.md).
- [PR #17](https://github.com/chrober/bliss-mood-poc/pull/17), [latest failed Windows job](https://github.com/chrober/bliss-mood-poc/actions/runs/39382026896).

## Working conventions and safety constraints

- Read **live** PR head and CI first: the handover describes a verified historical SHA, not necessarily the future tip of the branch.
- Keep changes on `feat/essentia-cpp-worker-backend`; do not merge PR #17 or change `main`. Keep it Draft.
- Prefer reusing upstream original C++, existing Rust multi-worker orchestrator and existing ONNX/single-writer code.
- For Windows PowerShell, wrap **every complete snippet** in a single outer `& { ... }`; use proper error checking.
- This project must not modify original `bliss.db` / NAS music; benchmarking must use read-only, explicitly capped cohorts and fresh sidecars.
- Record exact evidence for passed gates vs failed/skipped; no unsupported claim of Windows original Essentia end-to-end success.
- Be explicit when a CI failure is a new Windows linker issue versus existing green Linux or synthetic-fixture tests.
