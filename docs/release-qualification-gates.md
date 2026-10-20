# PR #17: release qualification after numerical real-MP3 parity

**As of 20 October 2026** · Branch `feat/essentia-cpp-worker-backend` ·
Draft [PR #17](https://github.com/chrober/bliss-mood-poc/pull/17).
This checklist separates proven numerical equivalence from the much broader
questions of **codec support, operating-system packaging, redistribution and
licensing**. Neither a successful numeric scan nor a CI fixture licenses a
production Windows/macOS/Linux release.

## Evidence and acceptance matrix

| Gate | Current decision | Evidence or condition for advancing |
| --- | --- | --- |
| Same real MP3 cohort, 100 tracks / 14,500 values, 4 Rust-v5 workers | **PASS** | Max class-score delta 1.2695789337158203e-5 vs saved original C++, tolerance 1e-3; 0 patch mismatches |
| Rust-v5 worker invariance, adaptive enabled 6 vs fixed 4 | **PASS** | 0.0 score difference across all 14,500 scores, identical patch counts and official model SHA. Controller sampled resources but made 0 adjustments |
| Adaptive-policy increase/decrease and stabilization on real music | **NOT DEMONSTRATED** | Actual run held 6 workers throughout; deterministic Rust unit tests cover simulated high/low loads, but dynamic changes under real controlled load have not been measured |
| Controlled real-song PCM24 WAV vs FLAC using same original signal | **PASS** | User's 20 October 2026 run: PCM24 SHA equal, 837 patches, both backends WAV vs FLAC score difference 0.0; C++ vs Rust v5 max 6.3700000000332935e-6 in each format (limit 1e-3). **Source was MP3-derived; not independent FLAC coverage.** |
| Windows x64 native C++ worker synthetic WAV/FLAC/MP3 fixture | **PASS (CI fixture)** | Verified original worker/ONNX handoff in native Windows workflow; does not substitute for real music |
| Real independent FLAC/WAV songs from the library | **OPEN** | A small, explicitly bounded and legally available sample with mixed rates/channels/bit depths, fresh Rust/C++ isolated sidecars, same ONNX SHA256 and max 1e-3 drift |
| Linux x86_64 original Essentia native smoke | **Partially validated** | Existing Linux CI numeric fixture, but portable packages, loader/library ABI and target distro matrix not release-qualified |
| macOS Intel / Apple Silicon, Pi 4 / piCorePlayer | **NOT QUALIFIED** | Native builds, loader/shared-library closure, ONNX runtime architecture, 1-worker memory, real-codec smoke |
| Redistributable native DLLs / `.so` / `.dylib` | **NOT LICENSE CLEARED** | Actual package dependency closure, exact source/versions, notices, counterpart source/build scripts, reproducible manifest; see licensing strategy |
| Essentia AGPL, Rust code provenance, FFmpeg/FFTW/libsamplerate licenses | **LEGAL REVIEW OPEN** | Consult `essentia-licensing-distribution-strategy.md`; test binaries are not automatically cleared for publication |
| MTG models (EffNet, Genre, Mood, Voice), weights and derived data rights | **RIGHTS OPEN** | Match downloaded exact SHA256 to each model license and separate terms for redistribution/noncommercial use |
| Stable multi-worker performance guarantee | **NOT MEASURED** | Existing 6-worker adaptive-enabled 92.8667 s vs prior 4-worker 183.2888 s is an uncontrolled between-run difference, NOT causal adaptive speedup |

**Release policy:** Do not quietly flip experimental-native DSP into a default
or advertise cross-platform/codec guarantees based solely on existing 100 MP3
parity. A merge of experimental code can be a separate explicit engineering
decision from bundling or distributing third-party binaries or model weights.
PR #16 similarity work remains separate.

## Verified controlled WAV24 / FLAC result — 20 October 2026

The user's real-song test **PASSED** on the exact source WAV and verified Rust-v5
and original C++ worker already present in the local Windows test kits:

| Measurement | Real outcome |
| --- | ---: |
| `status` | **PASS** |
| `pcm24_sha_equal` | **true** (bit-identical 24-bit PCM after independent decoding) |
| Patches, both backends / both formats | **837** |
| Original Essentia C++ vs corrected Rust v5 — WAV24 | **6.3700000000332935e-6** maximum class-score deviation |
| Original Essentia C++ vs corrected Rust v5 — FLAC | **6.3700000000332935e-6** |
| Rust v5 — WAV vs FLAC | **0.0** across class scores |
| Original C++ — WAV vs FLAC | **0.0** across class scores |

**Private report is local only** at
`D:\LMS\bliss-mood-poc\benchmark-real-wav-flac-v5-20261020-204139\private-codec-report.json`.
The controlled WAV24/FLAC pair comes from a **real song originally stored as MP3**.
The shared PCM control proves codec/container agreement for that signal,
but does not prove native independently sourced FLAC/WAV library coverage,
non-Windows portability or redistribution rights. **Do not re-run this
already PASSing gate** merely to check the report again.

The next data gap is a small set of **original, unmodified** FLAC/WAV files
sampled from the music NAS; see the native-lossless cohort gate below.

---

## First next gate: bit-exact decoded PCM across one real-song WAV24 and FLAC

The existing real audio example is a full-song WAV, originally decoded from
one of the confirmed failing real MP3s during resampler root-cause analysis.
Do **not** rescan all 100 MP3 songs again just to test lossless containers.

The new helper `scripts/verify_lossless_codec_parity.py`:

1. Validates original source PCM WAV hash and prior **genuine original
   Essentia C++** plus corrected **Rust v5** results, including their exact
   official encoder/head SHA256, ordered labels, preprocessing keys and
   equal full-song patch counts.
2. Quantizes the existing **float32 PCM** into exactly **one shared
   24-bit integer WAV**. Encodes FLAC **from that quantized WAV**.
   A float32 WAV and a FLAC do **not** intrinsically represent identical
   samples; quantization is therefore explicit rather than hidden.
3. Independently decodes WAV24 and FLAC back to signed 24-bit LE PCM using
   FFmpeg. Requires byte-for-byte identity, identical raw stream lengths,
   identical original sample rates and channel counts, or **fails before
   inference**. This does not compare arbitrary input files by filename.
4. Runs the validated **same Rust-v5 analyzer binary** four times:
   `wav24/rust`, `wav24/original C++`, `flac/rust`,
   `flac/original C++`, ONNX threads 1 and same model dir.
5. Verifies each format's C++/Rust parity, both individual backend's
   WAV-vs-FLAC score parity, all patch counts, fingerprint distinction and
   the unmodified original max per-class **0.001** tolerance.
6. Writes detailed private audio controls/JSON/stderr to **one fresh
   local directory**. The script reports a concise status and max scores;
   on any failure preserve the partial output for diagnosis rather than
   rescanning blindly.

This qualifies one *controlled original real-song signal through WAV24 and
FLAC decoding*. It does not prove the quality of independently sourced FLAC
collections or float-vs-PCM24 bit equivalence, and it is not a license grant.

### Reuse existing Windows development binaries, do NOT recompile or replace

Run in **Windows PowerShell**, with installed `python`, `ffmpeg` and
`ffprobe`, and the existing official model directory. Source music and the
original MP3 cohort are never accessed.

~~~powershell
& {
    $ErrorActionPreference = 'Stop'

    $repo = 'D:\LMS\bliss-mood-poc'
    $real = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $source = Join-Path $real 'mp3-wav-control-20261020-164836'
    $savedV5 = Join-Path $real 'rust-v5-one-track-20261020-190110'
    $rustKit = 'D:\LMS\bliss-mood-rust-v5-test'
    $nativeKit = 'D:\LMS\essentia-cli-test'
    $output = Join-Path $repo (
        'benchmark-real-wav-flac-v5-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    )

    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Cannot switch to PR17 branch' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Cannot update PR17 branch' }

    python -m unittest discover -s tests -p 'test_verify_lossless_codec_parity.py'
    if ($LASTEXITCODE -ne 0) { throw 'Lossless codec regression tests failed' }

    Get-Command ffmpeg -ErrorAction Stop | Out-Null
    Get-Command ffprobe -ErrorAction Stop | Out-Null

    $analyzer = Join-Path $rustKit 'bliss-mood.exe'
    $nativeWorker = Join-Path $nativeKit 'essentia-worker\bliss-essentia-worker.exe'
    $build = Join-Path $rustKit 'BUILD.txt'
    $sums = Join-Path $rustKit 'SHA256SUMS.txt'
    $mergeSha = 'a6a5c8607064e95d291cc85a0500472ff20bcc4e'
    foreach ($file in @($analyzer, $nativeWorker, $build, $sums)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Missing input: $file"
        }
    }
    if (-not (Get-Content -LiteralPath $build -Raw).Contains($mergeSha)) {
        throw 'Scanner is not the previously validated Rust-v5 build'
    }
    $line = Get-Content -LiteralPath $sums -TotalCount 1
    $m = [regex]::Match($line, '^([0-9a-fA-F]{64})\s+\*?bliss-mood\.exe\s*$')
    if (-not $m.Success) { throw 'Malformed scanner checksums' }
    if ((Get-FileHash -LiteralPath $analyzer -Algorithm SHA256).Hash -ine
        $m.Groups[1].Value) {
        throw 'Rust v5 scanner SHA256 mismatch'
    }

    $args = @(
        'scripts/verify_lossless_codec_parity.py',
        '--input-wav', (Join-Path $source 'control-from-mp3-decoded-float32.wav'),
        '--saved-cpp-wav-json', (Join-Path $source 'essentia-wav.json'),
        '--saved-rust-v5-wav-json', (Join-Path $savedV5 'rust-v5-full-wav.json'),
        '--analyzer', $analyzer,
        '--essentia-worker', $nativeWorker,
        '--models-dir', (Join-Path $repo 'models'),
        '--output-dir', $output,
        '--score-max-tolerance', '0.001'
    )

    Write-Host "`n=== ORIGINAL C++ VS RUST V5: REAL PCM WAV24 AND FLAC ==="
    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Lossless codec parity FAILED. Preserve private evidence at: $output"
    }
    Write-Host "`n=== WAV24 / FLAC CODEC GATE PASSED ==="
    Write-Host "Private results directory: $output"
}
~~~

Only paste the concise console JSON, especially `status`, `pcm24_sha_equal`,
`patches`, `wav24_cpp_vs_rust_max`, `flac_cpp_vs_rust_max`,
`rust_wav_vs_flac_max`, `cpp_wav_vs_flac_max`. Do not post source
music, raw PCM, full private class/track reports or third-party native
DLL archives.

## Second codec gate: two explicit independent lossless music downloads

**Initial 20 October 2026 result: PRE-INFERENCE FILTER, NOT PARITY FAILURE.**
The user provided a locally downloaded **48 kHz / 24-bit stereo FLAC**
and **44.1 kHz / 16-bit stereo WAV** of *different* songs. The WAV
also contains an MJPEG embedded-cover stream; the native test selects
the first audio stream via ffprobe `-select_streams a:0`.
The first test terminated at source selection: `Explicit .flac outside
bounded duration/size/rate limits`. The 48 kHz rate is explicitly
allowed; the old generic message did not distinguish a long song
(>420 seconds) from a large file (>150 MiB). No ONNX inference or
C++/Rust score comparison took place. No prior sidecars were touched.

**Correction:** For exactly two explicitly named lossless original
files, the helper now reports the *actual* duration/file size and the
specific violated limits. Explicit mode allows a deliberately bounded
`--max-seconds 1800 --max-file-mib 512` override, without widening
the automatic NAS traversal (still limited to 900 seconds). A song
over 1800 seconds or 512 MiB should be replaced with a shorter/smaller
original track, rather than trimming/transcoding it and calling it
an untouched original. The strict **0.001** score tolerance is unchanged.

The test script `scripts/verify_original_lossless_tracks.py` always:
- Reads **only** the two exact local FLAC/WAV sources; it does not
  reanalyze the prior 100-MP3 cohort, modify NAS or overwrite sidecars.
- Validates the existing genuine Essentia-C++/corrected Rust-v5 real
  WAV reference, exact ONNX weights/label order, native worker SHA and
  backend fingerprint; compares both models on each source (4 calls).
- Requires the exact same source audio SHA256 in the two backend
  reports, equal patch count and max per-class-score error <=0.001.
  Source file SHA256 is verified before and after scan.
- Retains full JSON/diagnostics locally in one new private folder.
  Track paths, titles and copied model/native binaries do not go
  into public GitHub logs. The MP3 twins are useful provenance but
  **cannot** be used as bit-identical PCM references.

### Ready-to-run Bandcamp retry, without NAS search

Place the two locally copied downloads as `sample.flac` and
`sample.wav` in `D:\LMS\bliss-mood-lossless-test`. In Windows
PowerShell run the existing single-block experiment with the following
additional flags inserted in the Python `$arguments` array:

~~~powershell
'--track', 'sample.flac',
'--track', 'sample.wav',
'--max-seconds', '1800',
'--max-file-mib', '512',
~~~

**Before rerunning**, print actual source metadata (no NAS scan):
~~~powershell
& {
    $root = 'D:\LMS\bliss-mood-lossless-test'
    foreach ($name in @('sample.flac', 'sample.wav')) {
        $file = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Missing downloaded source: $file"
        }
        $sizeMiB = (Get-Item -LiteralPath $file).Length / 1MB
        $info = ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate,channels,bits_per_raw_sample,bits_per_sample:format=duration -of json "$file" | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw "Audio probe failed: $name" }
        $seconds = [double]$info.format.duration
        Write-Host ("{0}: {1:N1}s, {2:N1}MiB, {3}Hz, {4}ch" -f $name, $seconds, $sizeMiB, $info.streams[0].sample_rate, $info.streams[0].channels)
        if ($seconds -gt 1800 -or $seconds -lt 30 -or $sizeMiB -gt 512) {
            throw "Original song is outside permitted bounded test: $name"
        }
    }
}
~~~

For a fully self-checking command, reuse the already provided Windows
test harness with exactly the new explicit bounds and the same
pinned executable/ONNX/C++ worker and saved real-WAV references. Do
not repeat the successful controlled WAV24/FLAC test.

## After the single controlled WAV/FLAC result

If it passes, preserve the evidence and select *a bounded real naturally
occurring FLAC/WAV sample* with different sample rates, durations and
channels for later testing. Do not present the converted test file as a
new independent library track. Reuse the comparison tools and official
models; prioritize the specific audio formats/platforms to be supported
before declaring any product-wide codec guarantee.

The [licensing/distribution strategy](essentia-licensing-distribution-strategy.md)
remains the source of outstanding legal release work. It deliberately
does not equate "users download the DLLs" with a categorical GPL/AGPL
compliance exemption.
