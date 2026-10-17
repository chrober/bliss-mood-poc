# bliss-mood-poc

Experimental Rust CLI for music mood analysis using MTG/Essentia Discogs-EffNet and MTG-Jamendo Mood/Theme ONNX models. It is being evaluated as an optional analysis sidecar for [bliss-rs](https://github.com/Polochon-street/bliss-rs) and Lyrion. Research/design context: [bliss-similarity-design](https://chrober.github.io/bliss-similarity-design/).

**Status:** experimental, not yet reference-validated; compilation and runtime integration are tracked by GitHub Actions. Do not use predicted scores for automatic production tagging or playlists until parity and quality checks have passed. No models are committed to Git.

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
bliss-mood scan --bliss-db .\bliss.db --db .\mood.db --models-dir .\models --library-root "/mnt/music" --source-root "D:\Music" --threads 4 --json
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

The PowerShell script downloads the ONNX encoder (~18 MB), Mood/Theme classifier (~2.7 MB), and its JSON class metadata from the official Essentia hosting. The model weights have **separate non-commercial licensing restrictions**, which must be reviewed before redistribution or commercial use. The source code in this repository is MIT.

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

**The Rust implementation is currently an approximation**. Exact Essentia parity is mandatory: compare a reference signal and intermediate features, then classification outputs. See `scripts/reference_essentia.py`, which requires Essentia TensorFlow and the separately downloadable `.pb` models.

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
