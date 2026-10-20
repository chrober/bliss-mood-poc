# Windows x64: original Essentia C++ worker packaging

**Status (2026-10-20):** Windows packaging and runtime DLL provenance checks implemented. Original Essentia C++ has NOT yet been successfully built for Windows; no Windows original-Essentia audio test has passed. Our Linux original Essentia C++ + WAV/FLAC/MP3 + all-head ONNX test is green: https://github.com/chrober/bliss-mood-poc/actions/runs/39373185587

## Windows native toolchain and blocker

The current Linux original Essentia C++ implementation uses pinned upstream commit `9ceef0a3a7900ad51eb42aa5b6c6789b4bec6a47`, which builds against Ubuntu 22.04's FFmpeg 4.4. Official Windows Essentia documentation recommends MinGW cross-compilation; the resulting MinGW C++ library cannot be directly linked to an MSVC Rust binary. Our subprocess IPC intentionally avoids C++ ABI sharing.

Current October 2026 MSYS2 MinGW64 distributes FFmpeg 9, incompatible with the pinned 2023 Essentia FFmpeg APIs. Newer MSYS2 Eigen/TagLib versions also require compatibility review. Do not claim a plain `pacman -S mingw-w64-x86_64-ffmpeg` installation produces a valid Windows Essentia worker. Either build a fully audited matching older native dependency set for this pinned original revision, or select a newer pinned original upstream revision and **re-run full C++/Rust DSP and model parity**.

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

## Remaining release validation gates

1. Build original Essentia C++ and pinned compatible dependencies for native Windows x64; record complete build provenance and package versions.
2. Create a self-contained package, then start it in a clean Windows environment **without** relying on a global MSYS2 directory in PATH. Verify handshake, multiple audio jobs and restart.
3. Re-run WAV/FLAC/MP3, Mel, 1280-D EffNet, 87+56+2 ONNX classification parity on Windows.
4. Run paired 1/2/4/6 Rust vs Essentia backend tests on the SAME bounded Bliss track cohort, observing CPU, combined private/RSS and cache effects.
5. Perform an independent license review and target-specific binary distribution validation. ARM64/piCorePlayer remains separate.

**Important:** CI currently tests the packager with synthetic Windows PE files and the multi-process Windows behavior with the standalone test fixture. These tests are not a successful original Essentia Windows build, and do not establish numerical parity for an unbuilt native Windows binary.
