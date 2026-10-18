# Essentia numerical validation gates

## Current status

- Windows ONNX CLI runs end-to-end against an NAS track, with complete-track inference.
- Incremental scan was verified using a new test database: pending -> analyzed -> skipped.
- The classifier is NOT numerically validated against Essentia; preserve experimental preprocessing version and false validation flag.
- The earlier Linux model-smoke workflow failed downloading official weights from essentia.upf.edu (curl timeout), not in the ONNX implementation.

## Gate 1: Deterministic log-Mel parity (automated GitHub Actions)

Workflow: .github/workflows/mel-parity.yml

1. Generate a deterministic 16-kHz, mono, 16-bit WAV on the GitHub runner.
2. Run the model-free Rust mel-dump CLI with 32 frames.
3. Run scripts/compare_mel_essentia.py against the same audio and official TensorflowInputMusiCNN.
4. Compare all 32 x 96 float values with relative and absolute tolerance 1e-3. Report MAE, RMSE, worst frame/band and fail on mismatch.

This tolerance follows an Essentia contributor's example at https://github.com/MTG/essentia/issues/1471 . Passing does not prove agreement on lossy decoding, boundary-frame padding, model embeddings or scores.

Upstream TensorflowInputMusiCNN source configures 512 FFT frame samples, non-normalized window, 96 bands, slaneyMel, linear frequency weighting, unit_tri normalization, shift=1, scale=10000, log10. Verify these numerical details against our Rust approximation before ever changing validation flags.

CI pins Python 3.11, NumPy 1.26.4 and Essentia 2.1b6.dev1389 (non-TensorFlow wheel) on GitHub-hosted Linux. No user music, trained models or local Python installations required for Gate 1.

## Gate 2: 1280-dimensional embeddings (not yet implemented)

Compare the official TensorFlow Discogs EffNet .pb embedding model and the ONNX embedding model on identical 128x96 patches. Account for fixed TensorFlow batch size 64 versus ONNX dynamic batch shape, padded final batches, and patch order.

## Gate 3: 56 Mood/Theme classes (not yet implemented)

Compare official TensorFlow classification-head probabilities and ONNX probabilities for the same embeddings. Require class-name alignment, per-patch tolerance, and full-track aggregation tolerance. Use a small diverse test corpus including synthetic signals and licensed/public-domain tracks.

## Gate 4: NAS and Pi operational readiness (not yet implemented)

Check modification-time identity Windows/SMB versus Linux mount, Pi AArch64 ONNX execution and benchmarks under playback, post-library-scan triggering, and plugin isolation. Do not launch the 65,000-track scan before preceding gates are satisfied.

## User tasks

None for Gate 1. The work runs on GitHub Actions. Local models, NAS audio, and Bliss/Mood SQLite files remain untouched.
