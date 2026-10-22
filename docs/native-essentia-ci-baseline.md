# Verified original Essentia C++ baseline — PR #18

**Baseline date:** 22 October 2026
**Validated PR head:** `c5df10b070174c1f844b9feb47b84c1ae8704724`
**Native workflow:** https://github.com/chrober/bliss-mood-poc/actions/runs/39787075901 (all stages PASS)
**Other successful runs at the same SHA:** [Voice](https://github.com/chrober/bliss-mood-poc/actions/runs/39787075964), [Genre](https://github.com/chrober/bliss-mood-poc/actions/runs/39787075939), [Rust checks](https://github.com/chrober/bliss-mood-poc/actions/runs/39787075844), [Windows binary](https://github.com/chrober/bliss-mood-poc/actions/runs/39787075920).

## Verified dependency identity

- Official unchanged MTG/Essentia C++ commit: `dc91e47ed634e0b152d3d0229ec86751bb315473` (14 October 2026).
- Official FFmpeg 9.0.2 source commit: `946fcce07b6dcd0331c8cc609192aeff5e1924f8`, linked libavcodec version `63.1.102`.
- Native CI runner: Ubuntu 24.04. The prebuilt static ONNX Runtime requires newer glibc/libstdc++ than Ubuntu 22.04.
- Native Essentia Waf configuration: upstream lightweight audio preprocessing with FFmpeg, libsamplerate and FFTW; no custom Essentia DSP port.
- Synthetic test-file encoder: separately pinned `imageio-ffmpeg==0.6.0`, reporting `ffmpeg 7.0.2-static`. An independent genuine `ffprobe` CLI supplies reference Rust decoder metadata. These fixture utilities **are not** the FFmpeg 9 libraries linked into native Essentia.

## Observed numerical and integration results

| Gate | Evidence |
| --- | --- |
| Four-patch C++ vs Rust Mel protocol | PASS; 49,152 coefficients; MAE **1.7774358e-07**, maximum error **8.4042549e-06** |
| WAV / FLAC / MP3 synthetic frontend | PASS; Mel MAE **6.3381264e-07–6.3811956e-07**, observed maximum **2.5510788e-05** |
| End-to-end Discogs EffNet + Mood + Genre + Voice comparisons | PASS on the same synthetic audio/official ONNX files |
| Production Rust scanner + original Essentia child processes | PASS |
| Fixed 1, 2 and 4 workers and adaptive mode initialized at 2 | PASS; observed peak active analyses 1, 2, 4, 2 |
| Stored score blobs and pooled 1280D embeddings across four worker configurations | **Exactly identical** |

In the original eight-song smoke, `adjustments=[]`. This is expected because
the conservative controller requires at least **24 completed tracks** and
**20 seconds** from its last capacity adjustment. Successful entry into
adaptive mode **does not demonstrate real dynamic resizing**.

## Remaining qualification

1. The newly added `scripts/verify_native_essentia_adaptive_long.py` uses
   **36** distinct synthetic 300-second tracks to observe actual, unmodified
   CPU/RAM samples and the controller's decision history. A green run with
   zero adjustments remains **inconclusive for real resizing**; the report
   explicitly records this. Never artificially manipulate resource samples
   or thresholds to force a PASS.
2. For operational performance, use a deliberately bounded representative
   local cohort: fixed **1/2/4/6** workers and adaptive, order balanced
   across repetitions, fresh sidecars, matched binaries/models and track
   sets, exact output parity, end-to-end time including startup and
   preworker resource baseline, and tree memory measurements. CI sine tones
   do not establish NAS throughput.
3. End-user binaries need a separate license/distribution review for
   FFmpeg, original Essentia, transitive libraries, ONNX Runtime, and
   platform-dependent ABI constraints. A green CI run is not a release.

PR #18 is stacked upon PR #17 and does not itself update main or the
PR #16 similarity research work.

## Local real-music performance benchmark (not executed in CI)

The standalone [native fixed-vs-adaptive benchmark](../scripts/benchmark_native_adaptive_manifest.py)
takes an **existing intentionally bounded 30–500-track** Bliss TracksV2
cohort database and exercises the original native C++ backend in a
balanced, deterministic order: fixed 1/2/4/6 workers and adaptive
(initial 2, limits 1–6) twice, with a reversed order on the second round.

Run this only on the machine that can read the sampled music and has
the tested native worker and official ONNX models. For example,
from the repository root (paths are illustrative and must be replaced):

```powershell
python scripts/benchmark_native_adaptive_manifest.py `
  --cohort-db "C:\\path\\sample-100.db" `
  --analyzer "C:\\path\\bliss-mood.exe" `
  --essentia-worker "C:\\path\\bliss-essentia-worker.exe" `
  --models-dir "C:\\path\\models" `
  --source-root "C:\\path\\music" `
  --output-dir "C:\\path\\benchmark-native-adaptive" `
  --plan-only
```

Remove `--plan-only` to run the full experiment. `--source-root` is
appropriate for relative `TracksV2.File` keys; add `--library-root`
only if the preexisting keys include an absolute LMS prefix that needs
remapping. Output must be new/empty; each configuration receives a fresh
SQLite sidecar and embedding directory. Scores, head fingerprints and
entire pooled 1280D embeddings **must match exactly** between modes.
The tool writes a local-only `summary.json`, `runs.csv`, and complete
per-run scanner logs, including controller adjustments and process-tree
memory diagnostics. It also verifies that the sampled input Bliss
database hash does not change.

**The script is prepared but real-music benchmarking has not been
run here** because the user's music and local native binaries are not
available to this session. Do not claim throughput gains, or upload
raw local reports or the private cohort database to the repository.
