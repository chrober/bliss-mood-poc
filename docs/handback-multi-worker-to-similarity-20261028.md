# Handback: static native multi-worker song analysis → Similarity PR #16

**Prepared 28 October 2026.** This file is the integration handback for the separate [Similarity Metric Evaluation PR #16](https://github.com/chrober/bliss-mood-poc/pull/16). PR #16's source, metrics, human listening comparisons and measurements are **not modified** by this work.

> **Release status is derived from the verified final `main` SHA, never from a draft feature branch.** Once the integration PR is merged, this handback must be updated with the actual `main` commit, successful workflow IDs, source/build fingerprint and artifact download instructions. Until that verification is recorded, the technical examples below describe the intended integration CLI rather than claim that `main` already contains it.

## What is integrated and what is deferred

The source integration combines [native Essentia C++ backend PR #17](https://github.com/chrober/bliss-mood-poc/pull/17) and stable functionality from [manifest/parallel embedding PR #18](https://github.com/chrober/bliss-mood-poc/pull/18) via [static integration PR #20](https://github.com/chrober/bliss-mood-poc/pull/20). Components include trusted persistent native C++ DSP worker IPC, reused model sessions for shared EffNet and Mood/Theme, Genre, Voice, a bounded fixed-capacity Rust worker coordinator, exactly one transactional SQLite writer, Bliss-catalog selection or read-only track manifest, resume/skip, private sidecar storage, strict path identity and 1280D normalized song embeddings. See [architecture and CLI guide](multi-worker-song-analysis-final.md).

**Not integrated:** ongoing worker count changes, experimental `--adaptive-policy resource/autotune`, `--adaptive-workers` and related min/max/song-gates, the isolated ONNX worker prototype and associated adaptive research in [PR #19](https://github.com/chrober/bliss-mood-poc/pull/19). Its four-campaign research log is [archived on that branch](https://github.com/chrober/bliss-mood-poc/blob/feat/ram-safe-online-autotune/docs/autotune-real-music-e2e-findings-20261028.md); the branch should not be deleted.

## Version and binary chain of custody

- **Integration PR:** #20; original stable source base `c4db3a5aa948f67ecbdeece435f479871ab9f496` (PR #18, which contains PR #17).
- **Final `main` commit:** **PENDING MERGE VERIFICATION** (do not infer an SHA).
- **Final verified Windows x64 source SHA and CI workflow run:** **PENDING**. The GitHub workflow builds `bliss-mood-windows-x64`; only use the artifact from a successful workflow tied to the final `main` code.
- **Executable SHA256:** read from the verified artifact's `SHA256SUMS.txt` and compare locally with `Get-FileHash`; do not substitute the GitHub ZIP artifact digest for the executable digest.
- **`BUILD.txt` checkout/source SHAs:** must agree with the verified source / build provenance for that exact artifact, including any merge-commit semantics.
- **Native worker EXE, models and label mappings:** independently fingerprint with SHA256 and record versions on the private machine. The scanner ZIP does **not** authorize or guarantee distribution of original Essentia native third-party dependencies.
- **Numeric parity:** require the actual final-commit Windows/Linux CI evidence below before interpreting results as validated. Old PR #17/18 CI are important provenance but not tests of the final static-only code.

## Windows provisioning and safe run

Retrieve the binary from the **successful final-commit Windows x64 workflow** under [Actions → Windows x64 binary](https://github.com/chrober/bliss-mood-poc/actions/workflows/windows-binary.yml), artifact `bliss-mood-windows-x64`. Extract to a new versioned local folder, verify `BUILD.txt` / `SHA256SUMS.txt` / `Get-FileHash`. Obtain official ONNX weights and JSON label maps separately. Install `ffmpeg` and `ffprobe` and provision the original Essentia C++ native worker **locally under an independently reviewed dependency/license regime**; do not publish or share unapproved native EXE/DLL bundles.

Use new **private** sidecar/embedding paths, never the original Bliss database as an output and never the user’s public audio/model directory. A manifest contains exact source-relative `TracksV2.File` keys, one per line, forward slash format, no duplicates or absolute paths. An example command after setting paths:

```powershell
$exe = '.\bin\windows-x64\VERIFIED\bliss-mood.exe'
$audio = 'D:\Music'
$native = '.\native\bliss-essentia-worker.exe'
$manifest = '.\private-similarity-cohort.txt'
$sidecar = '.\private-similarity-features.sqlite'
$embeddings = '.\private-similarity-embeddings'
New-Item -ItemType Directory -Force $embeddings | Out-Null
& $exe scan-features `
  --tracks-file $manifest --source-root $audio `
  --db $sidecar --embedding-dir $embeddings `
  --models-dir '.\models' --models moodtheme,genre,voice `
  --audio-backend essentia --essentia-worker $native `
  --workers auto --threads 1 --max-errors 3 --json
```

To read the Bliss database rather than a manifest, replace `--tracks-file` with `--bliss-db ...` and **omit `--embedding-dir`** (embedding export requires an explicit manifest). For a reproducible fixed worker count, replace `--workers auto` with `--workers 1`, `2` or `4`; never request more than process-visible logical CPUs. `--workers auto` is calculated **once** from visible logical CPUs and caps at eight; it is not throughput autotuning. The **default is 1**. Explicit non-native `--audio-backend rust` remains available but can yield distinct numerical DSP behavior; do not mix backend provenance in similarity evaluation.

Resume should skip already completed exact matches. A deleted embedding triggers only the missing output regeneration; a conflicting/corrupted output is an error, not an authorization to overwrite. Verify output sidecar schema and hashes and preserve the source manifest and model/native/CLI fingerprints privately for reproducibility. Use **read-only original Bliss/audio inputs**; avoid sensitive paths in public benchmark reports.

## Numerical evidence and constraints

- The original C++ / earlier Rust-v5 parity work reported max absolute score tolerance **0.001** on its selected 100-song scope; this is *tolerance-based comparison*, **not** a bitwise equality statement.
- Synthetic real-ONNX parity gates cover fixed 1/2/4 serialized score bytes and pooled 1280D JSON representation, with separate manifest resume/corruption tests. Exact CI results and job scopes from the **final integrated commit** must be recorded after merge.
- New source should preserve Mood/Theme **56D**, Genre **87D**, Voice **2D**, and normalized pooled audio embedding **1280D**, without changing model identities, patch count algorithm, source path identity or aggregation.
- The four experimental 100-song campaign reports (40 full scans) reported exact per-song output parity and different wall-time medians; they do **not** validate throughput benefit for an online controller or establish an optimal fixed worker count on arbitrary hardware.
- Only actual tested OS/architecture combinations can be described as verified. Windows CI build alone is not a native C++ Windows redistributable release approval.

## Legal/distribution warning — explicit and unresolved

The native development-kit license inventory has `license_inventory_complete=false`, `release_approved=false`, `distribution_release_status=BLOCKED`, including **17 native package notices still missing** from the installed collection. Native Essentia licensing, FFmpeg-linked dependencies, Rust transitive dependencies and third-party model notices/source obligations require independent compliance review. **The user explicitly requires source integration into `main` while retaining this documented risk; no unaudited EXE/DLL bundle may be publicly distributed as a result.** See [license strategy](essentia-licensing-distribution-strategy.md) and keep platform packaging gates intact.

## Dedicated prompt for PR #16

> Continue the **Similarity Metric Evaluation** in Draft PR #16 of `chrober/bliss-mood-poc`. First read `docs/handback-multi-worker-to-similarity-20261028.md` and `docs/multi-worker-song-analysis-final.md` from the actual `main` commit. Confirm the exact verified Windows x64 source/build/EXE SHA256 and native worker/model hashes, without modifying private Bliss/music inputs. Use `scan-features --tracks-file` with `--audio-backend essentia`, all three ONNX heads and `--embedding-dir` to prepare pooled 1280D song embeddings using `--workers auto` or a deliberately chosen fixed worker count, `--threads 1`. Do not work on dynamic worker autotuning, PR #19 or process isolation. Resume the planned mathematical and subjective comparisons of Mood/Genre/Embedding similarity metrics in PR #16. Do not change its existing human ratings and dataset unless explicitly instructed. Respect documented license/distribution and numerical parity limits. If the final binary/merge is still pending, report that honestly rather than substituting an experimental PR #19 build.

