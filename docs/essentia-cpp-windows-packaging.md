# Windows x64: original Essentia C++ worker packaging

**Verified status (2026-10-20):** The Windows packaging and DLL-provenance tests are green with a **synthetic** C++ fixture and a real imported DLL. The **original Essentia C++ library itself now compiles and links as `essentia.dll` under MinGW64**, but the real worker EXE still fails to link unresolved Essentia symbols. No Windows original-Essentia audio validation has passed. [Latest confirmed linker failure](https://github.com/chrober/bliss-mood-poc/actions/runs/39382026896) · [Next-action runbook](handover-essentia-windows-linker-20261020.md). Linux original-Essentia C++ plus WAV/FLAC/MP3 and all-head ONNX comparison remains green: https://github.com/chrober/bliss-mood-poc/actions/runs/39373185587

## Windows native toolchain and blocker

The current Linux original Essentia C++ implementation uses pinned upstream commit `9ceef0a3a7900ad51eb42aa5b6c6789b4bec6a47`, which builds against Ubuntu 22.04's FFmpeg 4.4. Official Windows Essentia documentation recommends MinGW cross-compilation; the resulting MinGW C++ library cannot be directly linked to an MSVC Rust binary. Our subprocess IPC intentionally avoids C++ ABI sharing.

Current October 2026 MSYS2 MinGW64 distributes FFmpeg 9, incompatible with the pinned **2023 Linux reference** Essentia FFmpeg APIs. The experimental Windows workflow instead builds **original upstream Essentia at `b0661db99be4a8e2c6fabbe90a996f89786fdd8e` (unmerged upstream PR #1540)**, with `--std=gnu++14 --lightweight=libav,libsamplerate,fftw`. This upstream library build **succeeded** in run #39382026896, but the separate real worker EXE **failed to link**. This newer source revision requires independent Windows DSP and ONNX numerical parity before release; a successful DLL alone is not enough. MSYS2 dependencies are rolling and must be recorded and audited.

References:
- https://essentia.upf.edu/installing.html
- https://github.com/MTG/essentia/blob/master/FAQ.md
- https://packages.msys2.org/packages/mingw-w64-x86_64-ffmpeg

## Packaging after a real native EXE exists

`scripts/package_essentia_worker_windows.py` is a PE/DLL dependency packager, NOT an Essentia compiler. It requires a real original-Essentia x64 worker, GNU `objdump -p` and explicit, trusted dependency directories containing all transitive native runtime DLLs.

Example, PowerShell, from the project root:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location 'D:\LMS\bliss-mood-poc'
    $worker = 'D:\native-build\bliss-essentia-worker.exe'
    $objdump = 'C:\msys64\mingw64\bin\objdump.exe'
    $mingwDllDir = 'C:\msys64\mingw64\bin'
    $nativeDllDir = 'D:\native-build\lib'
    $out = 'D:\LMS\essentia-worker-x64-experimental'

    py -3 .\scripts\package_essentia_worker_windows.py `
        --worker $worker `
        --objdump $objdump `
        --dll-dir $mingwDllDir `
        --dll-dir $nativeDllDir `
        --output $out
    if ($LASTEXITCODE -ne 0) { throw 'Native Essentia DLL closure incomplete' }

    py -3 .\scripts\package_essentia_worker_windows.py --verify $out
    if ($LASTEXITCODE -ne 0) { throw 'Native worker package hash mismatch' }
}
~~~

The packager recursively parses the Windows x64 PE import tables, refuses missing/ambiguous DLLs, path escapes, wrong architectures, MSYS/Cygwin runtime dependencies, and oversized DLL sets. It writes a versioned `worker-dependencies.json` with SHA-256 and file sizes for the original worker and all copied non-system DLLs. The worker EXE and DLLs are copied side-by-side. It never searches arbitrary PATH directories for dependencies.

**On Windows the Rust scanner requires that manifest** for explicit `--audio-backend essentia`. It checks all named EXE/DLL bytes before selecting the backend. The generated native deployment manifest SHA256 is included in the model identity *in addition to* the existing native worker executable SHA256. Updating a native DLL invalidates stale feature-cache identities; altering a file without updating the manifest fails before analysis. The existing Rust backend remains the default and needs no C++ libraries.

## Licensing

Without a separate license inventory the bundle is for **development only**. Optionally pass `--license-map inventory.json`, mapping every lowercase binary name to `{"spdx":"SPDX-Identifier","notice_file":"relative-path.txt"}`. The packager validates the file inventory and copies the supplied license notices to `LICENSES/`. The manifest always contains `release_approved=false`: a complete mechanical inventory is **NOT** a legal release review.

Essentia itself is AGPLv3; native FFmpeg, FFTW, TagLib, Chromaprint and other linked dependencies have separate licensing obligations. The Rust orchestrator's MIT license does not automatically eliminate these. No native Windows worker package may be described as production-approved or uploaded as a release without an explicit audit.

## Windows executable/DLL packaging smoke: verified

The independent native packaging gate
[Actions run #39377432281](https://github.com/chrober/bliss-mood-poc/actions/runs/39377432281)
completed **successfully** on Windows Server 2022. It compiled a genuine
Windows x64 PE **synthetic IPC fixture** using MSVC, discovered and inspected
the actual PE imports using MSYS2 MinGW64 GNU objdump, resolved and packaged
its transitive DLL closure, verified the generated SHA256 manifest and
launched the *copied, bundled* executable to confirm the exact EFW1 protocol
handshake. No Essentia C++ source was compiled in this packaging test.

The Rust Windows tests separately verify that missing
`worker-dependencies.json` and post-packaging changes to a bundled DLL
prevent backend selection, while a correctly hashed native package
produces a distinct deployment-based feature model identity. These
tests guard installation/version drift but are **not** proof of
original Essentia Windows portability.

## Remaining release validation gates

1. **Fix original Essentia C++ Windows worker EXE linking** to the already built original `essentia.dll`: inspect exports, MinGW import library, CMake link line and ABI. Record full build provenance.
2. Create a self-contained package, then start it in a clean Windows environment **without** relying on a global MSYS2 directory in PATH. Verify handshake, multiple audio jobs and restart.
3. Re-run WAV/FLAC/MP3, Mel, 1280-D EffNet, 87+56+2 ONNX classification parity on Windows.
4. Run paired 1/2/4/6 Rust vs Essentia backend tests on the SAME bounded Bliss track cohort, observing CPU, combined private/RSS and cache effects.
5. Perform an independent license review and target-specific binary distribution validation. ARM64/piCorePlayer remains separate.

**Important:** The synthetic native DLL-closure smoke is validated, and the original upstream Essentia library now builds on Windows. Neither result proves that the **real Essentia-linked worker EXE** links or runs; Windows original-Essentia audio and full numeric parity remain open.
