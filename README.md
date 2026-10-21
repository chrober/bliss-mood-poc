# bliss-mood-poc

Experimental Rust CLI for capability-based music feature analysis using MTG/Essentia Discogs-EffNet and MTG-Jamendo Mood/Theme and Genre plus Voice/Instrumental ONNX classification heads. It is being evaluated as an optional analysis sidecar for [bliss-rs](https://github.com/Polochon-street/bliss-rs) and Lyrion. Research/design context: [bliss-similarity-design](https://chrober.github.io/bliss-similarity-design/).

**Status:** experimental; deterministic synthetic-audio numerical parity has passed against official Essentia/TensorFlow, but real-music quality and production suitability are not validated. Compilation and runtime integration are tracked by GitHub Actions. Do not use predicted scores for automatic production tagging or playlists until parity and quality checks have passed. No models are committed to Git.


## Development handover (2026-10-19)

For ongoing scanner performance work, start with
[docs/chat-handover.md](docs/chat-handover.md) and the detailed
[adaptive scanner benchmark and investigation handover](docs/adaptive-scan-performance-handover.md).
These documents capture the fixed 6/8/10/12-worker NAS benchmarks, the first
adaptive run (100 songs, 6 -> 6 workers, slower than fixed 6), the actual
CPU/RAM gating rules, verified invariants, and the next experiments.
The unchanged worker count is *consistent with the current thresholds*;
the throughput regression is not yet diagnosed. Check the current main
commit and source before concluding otherwise.


## Lyrion integration workstream (current priority)

The first **integration experiment** uses Bliss-first playlist generation
with independent Mood/Theme and Genre guidance in Lyrion through the
existing BlissMixerLab provider host. **Bliss-first, Mood-/Genre-first and
Hybrid remain open alternative mixing strategies; no final product choice
has been made.** See the [functional integration plan](docs/lyrion-bliss-mood-genre-integration.md):
its first gate is a read-only schema-v3 feature lookup and **exact**
`TracksV2.File` mapping for candidates and anchors. It must not change
production Bliss Mixer, invoke ONNX at mixing time, or silently use
unvalidated predictions. The [cross-platform resources plan](docs/platform-resource-roadmap.md)
is recorded for later and does not block functional integration.

## Generic feature models (opt-in)

The **feature analyzer** is separate from the legacy Mood-only commands.
The capability-based registry in [model-registry.json](model-registry.json)
defines model IDs, semantic capabilities, shared encoder, ONNX heads,
class metadata, and expected class counts. It currently declares:

- **moodtheme**: MTG-Jamendo Mood/Theme, 56 labels, capability mood_theme.
- **genre**: MTG-Jamendo Genre, 87 labels, capability genre.
- **voice**: Voice/Instrumental, 2 labels, capability voice_presence, Softmax.

All three use **one** Discogs-EffNet 1280D embedding pass per song.
The registry declares an output type per head: Mood/Theme and Genre are
independent Sigmoid multi-label outputs; Voice/Instrumental is a **two-class
Softmax distribution**. Each output type has a separate aggregation identity
and per-head model fingerprint, so the existing Mood/Genre cache keys remain
unchanged. Scores across different models must **not** be directly added or
interpreted as calibrated probabilities. Further compatible 1280D ONNX heads can be registered without
hardcoding their labels in the inference engine. Different encoder families
require additional feature-extractor support.

Download the seven official runtime files (encoder, three heads and their
metadata) using the existing PowerShell download script. Model weights
and music are not committed to Git.

Read-only analysis without any SQLite modification:

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    .\bliss-mood.exe analyze-features 'D:\Music\track.flac' --models-dir .\models --models moodtheme,genre,voice --threads 2 --json
}
~~~

Optional generic write: add --db .\mood.db and --track-key with the
**exact** TracksV2.File value. Back up mood.db before the first write.
An additive migration to SQLite schema v3 preserves all legacy Mood score
and scanner-state rows. New classifier scores go into feature_tracks and
feature_track_state, each keyed by (track_file, model_id). A successful
multi-model write is committed in one transaction. The old analyze and scan
commands remain Mood-only. The old db-coverage command reports the legacy
Mood table, not the new generic feature coverage.

Example read-only incremental preview:

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    .\bliss-mood.exe scan-features --bliss-db .\bliss.db --db .\mood.db --models-dir .\models --models moodtheme,genre,voice --source-root '\\192.168.1.100\music' --max-new 12 --dry-run --json
    # Remove --dry-run only after checking the output and backing up mood.db.
}
~~~

Read-only real-song quality sampling without any SQLite writes:

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    python .\scripts\sample_mood_quality.py --bliss-db .\bliss.db --source-root '\\192.168.1.100\music' --exe .\bliss-mood.exe --models-dir .\models --models moodtheme,genre,voice --count 12 --output .\mood-quality-sample-dual.csv
    Import-Csv .\mood-quality-sample-dual.csv |
        Select-Object track_key, status, top5, genre_top5, voice_top5, total_seconds |
        Format-List
}
~~~

The Mood top5 field and its original unprefixed 56 score columns are retained.
Additional genre_top5 and genre:<class> columns cover the 87 Genre scores;
voice_top5, voice:voice and voice:instrumental cover the Softmax output.
The Voice model does **not** identify vocal techniques such as growling,
screaming or clean singing, and a whole-song score is not a temporal measure
of the amount of singing.
The diagnostic CSV is gitignored. A separate
[genre parity workflow](.github/workflows/genre-parity.yml) compares the
new head and all end-to-end Genre scores against official Essentia TensorFlow
reference weights. A corresponding [Voice parity workflow](.github/workflows/voice-parity.yml)
validates the new Softmax head against the official TensorFlow reference without storing weights or user music in Git.

The new scores remain experimental and unvalidated for production playlist
generation; adding the Genre analyzer does **not** modify BlissMixerLab,
the existing Guidance SPI, or any production mixing strategy.

## Parallel offline analysis with interactive CPU headroom

Parallelism is opt-in and currently implemented for generic
scan-features (Mood, Genre, Voice) and the read-only quality sampler.
Legacy Mood-only scan stays unchanged.

The options have different meanings:

- **--workers auto** parallelizes **across songs**. For scan-features, auto
  reserves at least two logical CPUs when possible and about 25% of logical
  capacity, with a maximum of eight workers. On Windows, automatic mode also
  sets the analysis process to the BelowNormal priority class. Explicit
  workers 1..64 are supported, with no automatic priority adjustment.
- **--threads 1** sets the ONNX intra-op threads per worker. For parallel
  analysis, threads > 1 are intentionally rejected to avoid oversubscription.
- **--max-new 12** now limits **new analysis attempts** (whether they
  succeed or fail), not just successful commits. A benchmark limited to 12
  songs will never analyze 13 because a model is broken. Existing up-to-date
  entries do not consume this budget.
- **--max-errors 5** (default) stops a faulty scan after five encountered
  source, mapping, decoding or inference errors. This prevents a misconfigured
  model or a disconnected music share from traversing the entire library.
  Tune only when deliberately tolerating many faulty files. **--dry-run**
  makes no SQLite writes and does not start analysis sessions.

All workers share exactly **one process-wide ONNX Runtime environment**;
each worker owns and reuses its own ONNX sessions. Earlier Windows builds
could fail with "only one environment is allowed per process" when many
workers initialized at once. Do not use those builds for parallel scanning.
The fixed implementation is covered by an eight-worker initialization test.

A separate set of ONNX sessions is reused by each worker. The dispatcher
keeps at most one in-flight song per worker, bounding decoded-audio memory.
A single coordinator writes SQLite; the source Bliss DB and audio are
read-only. The auto policy is a **heuristic**, not real-time CPU/RAM monitoring.
If interactive response, NAS throughput, or laptop temperature are inadequate,
try an explicit smaller worker count (2 or 3). Use a local SSD sidecar; back
up mood.db before any first writable analysis.

PowerShell trial (replace the executable path with your downloaded current
Windows artifact; the model registry must contain all three models):

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    $exe = '.\bin\windows-x64\LATEST-RUN-ID\bliss-mood.exe'
    & $exe scan-features --bliss-db .\bliss.db --db .\mood.db --models-dir .\models --models moodtheme,genre,voice --source-root '\\192.168.1.100\music' --workers auto --threads 1 --max-new 12 --dry-run --json
    # Remove --dry-run only after checking the result and backing up mood.db.
}
~~~

The read-only sample tool also supports --workers auto, but limits itself to
four child processes because each process loads separate ONNX models.
On Windows, the child processes use BelowNormal priority. Output CSV rows
remain deterministically ordered and are written by one parent process.
For parallel sampling use --workers auto --threads 1; default --workers 1
keeps previous CLI behavior.

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    python .\scripts\sample_mood_quality.py --bliss-db .\bliss.db --source-root '\\192.168.1.100\music' --exe .\bliss-mood.exe --models-dir .\models --models moodtheme,genre,voice --count 12 --workers auto --threads 1 --output .\mood-quality-parallel.csv
}
~~~

## Native scanner diagnostics and optional adaptive concurrency

The Rust scan reports **stage totals** in its JSON diagnostics: FFprobe/
FFmpeg decode (includes file/network I/O), Mel + patch preparation, ONNX
inference, SHA-256 audio re-read, and per-worker ONNX session load. Values
are **sums of overlapping per-song wall times**, not exclusive CPU times.
They must not be compared directly to whole-scan wall time. Audio hashing
performs a second full read of every source audio file; high decode/hash
fractions are consistent with I/O constraints, not proof of NAS saturation.
Windows and Linux sample system-wide CPU and physical RAM about every two
seconds as classification results arrive.

By default fixed --workers behavior remains unchanged. The opt-in flag
**--adaptive-workers** dynamically changes the number of concurrent
in-flight tracks. Per-worker ONNX sessions are reused and SQLite still has
one writer. For the measured HP Ryzen 7 7730U with 16GB memory, start at
six workers and permit a guarded range of four to eight. In adaptive mode
Windows sets the analyzer process priority to BelowNormal.

~~~powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    $exe = '.\bin\windows-x64\LATEST-RUN-ID\bliss-mood.exe'
    & $exe scan-features --bliss-db .\bliss.db --db .\adaptive-test.db --models-dir .\models --models moodtheme,genre,voice --source-root '\\192.168.1.100\music' --workers 6 --adaptive-workers --min-workers 4 --max-workers 8 --threads 1 --max-new 100 --max-errors 3 --json
}
~~~

The controller requires at least 24 completed songs. It lowers active
concurrency by one after two consecutive samples at 88% RAM or 90% CPU.
It raises by one only after three samples below 79% RAM AND 65% CPU.
Adjustments require at least a 20-second cooldown to avoid oscillation.
Decisions are logged as ADAPTIVE WORKERS and recorded under the JSON
diagnostics adjustments field. No active task is cancelled and no ONNX
environment is recreated. On a system already around 85% RAM it should
usually hold the six-worker baseline. This is a **protective resource
heuristic, not a proven real-time throughput optimizer**; compare controlled
equal-work scans to infer optimum worker settings. Missing OS metrics cause
the controller to hold current concurrency. Fresh sidecar databases are
necessary for honest benchmark comparisons.

## Windows executable without local Rust/Visual Studio

The [Windows x64 binary workflow](https://github.com/chrober/bliss-mood-poc/actions/workflows/windows-binary.yml) builds the release executable on a **GitHub-hosted Windows Server 2022 runner**, using MSVC 2022. The job runs Rust tests and verifies that the binary and scan subcommand start before publishing anything.

To download: open the latest **successful** run, scroll to **Artifacts**, and download **bliss-mood-windows-x64**. Extract the GitHub ZIP; it contains bliss-mood.exe, BUILD.txt, SHA256SUMS.txt, a short Windows guide, and any ONNX Runtime DLLs needed by the linked configuration. No local Rust toolchain, Cargo build, or VS Build Tools are necessary.

Run bliss-mood.exe from the project directory with --models-dir pointing at your **separately downloaded** models/ directory. FFmpeg **and ffprobe** must still be available via PATH (both ship with typical full FFmpeg distributions). The artifact does **not** include model weights or music, and it is not a Pi binary.

PowerShell example:

    Set-Location 'D:\LMS\bliss-mood-poc'
    $key = 'Acid Mammoth/2024 - Supersonic Megafuana Collision/04 Atomic Shaman.mp3'
    $song = Join-Path '\\192.168.1.100\music' ($key -replace '/', '\')
    .\bliss-mood.exe analyze $song --models-dir .\models --threads 2 --max-patches 10 --db .\mood-test.db --track-key $key --json

This is a build/startup smoke test and experimental model inference, **not** reference validation against Essentia.

## Real NAS smoke test (relative Bliss paths)

Your Lyrion `TracksV2.File` values may be **relative** to the NAS music root (for example, `Acid Mammoth/2024 - Supersonic Megafuana Collision/04 Atomic Shaman.mp3`). In that case supply **only** `--source-root` to batch scans, with `--library-root` omitted.

The Windows source root can be a UNC share such as `\\192.168.1.100\music`; the Pi uses its mounted directory as the source root. The Mood database stores the original relative Bliss keys verbatim on either platform. Run the [exact Windows NAS smoke test](docs/windows-nas-smoke-test.md) before scanning the full collection.

## Setup (Windows)

Install Rust stable and FFmpeg (available on PATH), then:

```powershell
.\scripts\download-models.ps1
cargo test
cargo run --release -- analyze "D:\Music\song.flac" --models-dir models --threads 1 --json
```

### Hybrid batch analysis: workstation bootstrap, Pi incremental scan

The *same* Rust binary can create the initial database for ~65,000 songs on a faster host and continue incrementally on the Raspberry Pi 4B after library scans. The future Lyrion plugin post-scan trigger is not installed yet.

Desktop bootstrap (use the *actual* paths from your Bliss database, not the example values):

```powershell
bliss-mood scan --bliss-db .\bliss.db --db .\mood.db --models-dir .\models --source-root "\\\\192.168.1.100\music" --threads 4 --json
```

Read-only preview of imported database on Pi:

```sh
./bliss-mood scan --bliss-db /path/bliss.db --db /path/mood.db --models-dir /path/models --threads 1 --dry-run --json
```

Incremental analysis on Pi:

```sh
nice -n 15 ./bliss-mood scan --bliss-db /path/bliss.db --db /path/mood.db --models-dir /path/models --threads 1 --max-new 20 --json
```

The batch scanner reuses both ONNX sessions across songs and skips existing entries when path, file size, modification timestamp and model fingerprint match. It never writes to `bliss.db`. SQLite schema v2 migrates previous v1 databases in place. A mismatched Windows/SMB modification timestamp may make the Pi think many imported tracks changed; **run the dry-run before enabling post-scan automation**. See [hybrid Pi/Lyrion architecture](docs/lyrion-hybrid-analysis.md).

### Optional SQLite sidecar for Lyrion

After the audio inference is working and has been validated against the Essentia reference, write results into a **separate** `mood.db`:

```powershell
cargo run --release -- analyze "D:\\Music\\Rock\\Song.flac" --models-dir models --db mood.db --track-key "/mnt/music/Rock/Song.flac" --threads 1 --json
cargo run --release -- db-coverage --db mood.db --bliss-db "D:\\Backup\\bliss.db" --json
```

`--track-key` is the exact corresponding `TracksV2.File` value on the Lyrion host, not the Windows source path; a future batch mode will automate audited root mappings. `--db` and `--track-key` must be passed together. An accidental `bliss.db` target containing `TracksV2` is rejected. The coverage command opens both databases **read-only**. The current analyzer marks its rows **experimental / not Essentia-validated**; production mix consumers must reject those scores until verification is complete.

Storage uses a versioned SQLite schema, one row per song, a separate model/provenance catalog and 224-byte score vectors. Copy the fully closed database to the Pi via a staged/atomic replacement, then load the cached values at mix time; the Pi needs no ONNX dependency for retrieval. See [offline architecture](docs/offline-mood-database.md).

The PowerShell script downloads the ONNX encoder (~18 MB), the Mood/Theme, Genre and Voice classification heads, and all three class-metadata JSON files from official Essentia hosting. The model weights have **separate non-commercial licensing restrictions**, which must be reviewed before redistribution or commercial use. The source code in this repository is MIT.

## CLI and JSON

```
bliss-mood analyze SONG [--models-dir models] [--threads 1] [--max-patches 10] [--json]
```

- `--threads` caps ONNX CPU inference threads, important for a shared Lyrion host.
- `--max-patches` limits the *inference* to N initial audio patches; decoding and feature extraction still process the entire track.
- JSON includes all 56 class scores, audio and model SHA-256 hashes, patch count, and separate **decode / DSP / model load / inference / total timings**.
- `validated_against_essentia: false` explicitly identifies the experimental preprocessing pipeline.
- Audio files are never modified.

## Model pipeline

FFmpeg decode/resample to 16 kHz mono float PCM; windowed 512-point FFT, 256-hop, 96 Mel bands, log10 transform; 128 × 96 input patches with 62-frame hop; 1280-dim Discogs-EffNet embeddings; 56-dimensional Mood/Theme classification; arithmetic mean of patch probabilities.

**Numerical parity has passed for the test fixtures** (Mel features, EffNet embeddings, 56-class head, and full tracks in 16 kHz mono WAV and 44.1 kHz stereo WAV/FLAC/MP3). Rust decodes native float PCM using FFmpeg, explicitly averages stereo at 0.5/0.5 and reproduces Essentia's streaming SRC_LINEAR resampling phase in Rust. These are synthetic, music-like signals, **not** real-world genre/mood quality evidence; the stored validation flag remains false. See [Essentia validation details](docs/essentia-validation.md).

## Numerical validation against Essentia

The Mel frontend has passed a numerical parity test against the official Essentia TensorflowInputMusiCNN (32 x 96 values on deterministic synthetic WAV): MAE 8.71e-7, maximum difference 1.85e-5. See [validation gates](docs/essentia-validation.md).

Gate 2 has passed the [full-signal embedding parity workflow](https://github.com/chrober/bliss-mood-poc/actions/runs/39114494745): four 1280-dimensional Discogs-EffNet embeddings (5,120 values) matched Essentia's TensorFlow .pb model, with identical patch count. Gate 3 also passed the [56-class classifier parity test](https://github.com/chrober/bliss-mood-poc/actions/runs/39114008062): four patches and all mean Mood/Theme scores matched. These are deterministic synthetic-audio tests, NOT a real-music quality evaluation; normal Mood scores remain experimental. The models are downloaded on runners, never committed to Git.

A diagnostic command exports ONNX embeddings without touching any SQLite database:

    bliss-mood embedding-dump some-audio.wav --models-dir models --max-patches 4 --threads 1 > embeddings.json

This diagnostic requires only discogs-effnet-bsdynamic-1.onnx, not the Mood/Theme classifier. Avoid running large library scans until embeddings and all 56 classification outputs have been verified.

## Local quality review using real NAS songs

The read-only sample runner selects an unbiased seeded random subset from a **local copy** of bliss.db and calls the current Windows binary's analyze command with NO --db option. It only writes a local CSV file; neither bliss.db nor the existing mood.db is altered. The CSV can contain your artist/album/file names, so it is excluded from Git.

In PowerShell, after downloading the latest successful Windows binary through GitHub Actions:

    Set-Location 'D:\LMS\bliss-mood-poc'
    python .\scripts\sample_mood_quality.py --bliss-db .\bliss.db --source-root '\\192.168.1.100\music' --exe $exe --models-dir .\models --count 12 --output .\mood-quality-sample.csv

When reviewing results, compare the top five classes to the songs you know, especially heavy, energetic, dark, mellow/relaxing and melancholic material. Sample selection is deterministic with seed 20261018; increase --count to 50 or 100 for a broad exploratory review, but quality assessment is subjective and cannot be inferred from numeric model parity alone. Do not commit or upload the private CSV or your music files automatically.

## Raspberry Pi 4 / Lyrion

See **[Pi 4B and piCorePlayer performance benchmark](docs/raspberry-pi-benchmark.md)**. We have not measured actual throughput on a Pi 4B yet. AArch64 is the primary target, with ONNX Runtime deployment/linker compatibility to be verified. Until then, the safest strategy is offline batch analysis on another computer and cached scores for Lyrion.

## Research gates

1. Rust build, formatting, tests, and CI.
2. ONNX end-to-end inference on a real file.
3. Numerical parity against Essentia and stable score semantics.
4. Mood-quality evaluation (50–100 diverse songs), comparison with Bliss and sonara.
5. Pi4 CPU/RAM/temperature/per-song benchmarks under Lyrion playback.
6. Optional versioned sidecar cache and mood-aware re-ranking without changing Bliss's established 23D vector.

No production Lyrion or bliss-rs components are altered by this PoC.

### Detailed Discogs400 genres

The official [Discogs400 model directory](https://essentia.upf.edu/models/classification-heads/genre_discogs400/)
currently provides the Discogs-EffNet classification head as TensorFlow
`genre_discogs400-discogs-effnet-1.pb`, plus class metadata, but not an
ONNX head. It contains fine-grained genres such as Black Metal, Post-Metal,
Atmospheric Black Metal and Psychedelic Rock. It is **not enabled** by this
extension: an explicit, reproducible TF-to-ONNX conversion, numerical parity
check and model provenance verification would be required first. The current
Mood, Genre and Voice ONNX pipeline must not silently try to load a
non-existent official Discogs400 ONNX file.

## Offline Mood/Genre similarity metric benchmark

Before activating a Mood/Genre guidance weight, compare RMS, cosine,
centered cosine, weighted Jaccard and sparse top-K weighted Jaccard
**separately for the 87D Genre and 56D Mood heads**. The new
[read-only similarity evaluator](docs/similarity-metric-evaluation.md)
runs with Python's standard library against the existing schema-v3
feature database, with a deterministic sample, optional human-judged
positive/negative pairs, and no audio/ONNX work. It deliberately
**does not choose a winner or calibrate scores without real listening
judgments**. Current model outputs remain experimental.

The [listening-pair pilot generator](scripts/propose_similarity_listening_pairs.py)
can prepare a small deterministic **unlabeled** CSV with separate Genre/Mood
judgments, and a sealed private audit that must not be inspected before
listening. It can use the numerically checked Rust-v5 real-MP3 schema-v3
sidecar **directly** without merging experimental native Essentia C++
PR #17, running ONNX, rescanning music or modifying SQLite. The sampling
deliberately includes head/metric disagreements, low Mood activations and
random controls. Its curated pairs are **not** an unbiased held-out
benchmark or proof of a metric winner. See
[exact Windows command and methodology](docs/similarity-metric-evaluation.md#21-october-2026--restart-on-numerically-checked-rust-v5-vectors-pr-17-not-required).

## Local files and Git hygiene

`.gitignore` excludes root-level `benchmark-*/` benchmark runs,
`bin/` GitHub Actions downloads, `models/` weights, locally populated
SQLite databases, `mood-full.json` and root `mood-quality-*.csv`
exports. These can contain library filenames or user-specific metadata;
never commit them. Tracked fixtures, code and model registry JSON are not
blanket-ignored.

**`Cargo.lock` is deliberately not gitignored.** Since this repository
builds distributable Rust executables, commit the generated lockfile once
to freeze dependency resolution across developer machines and CI. If
`Cargo.lock` still appears as untracked, that is the single intentional
exception; do not hide it through `.gitignore` or `.git/info/exclude`.
