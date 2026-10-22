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
   **36** distinct synthetic 120-second tracks to observe actual, unmodified
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
