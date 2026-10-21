# GitHub Actions trigger, failure and worker audit — 2026-10-21

## Summary

Scope: Draft PR #16 branch `feat/similarity-metric-evaluation`.
Do not merge main, PR #13 or PR #17. No local Rust build and no
user-library audio processing.

### Real FMA-Small failure

[Run 39581435733 / job 119159724215](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733/job/119159724215):

- Official metadata and FMA-Small ZIP downloaded successfully (12 and
  8,002 archive members respectively).
- Corrected, pinned Rust-v5 build and Genre ONNX downloads succeeded.
- Before inference, `scripts/benchmark_fma_genre.py:match_audio` raised
  `ValueError: Suspicious FMA audio member size`.
- Cause: one unexpectedly small/large audio member caused an **entire**
  FMA validation to stop, even when not selected.
- Fix: ignore and count isolated suspicious audio ZIP members; require
  **no more than 50 anomalies** and **no more than about 1% or 50 missing
  track members** in total (for FMA-Small 8,000 tracks, at least 7,950
  usable members). Missing genres, candidate shortages and duplicate
  member identities remain hard errors. Selection remains deterministic
  and only uses accepted inputs.
- Synthetic regression tests cover isolated tiny/corrupt entries and
  unacceptable archive damage, in the separate Python CI workflow.
- Corrected FMA branch-run URL:
  https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757.
  **The final result must be checked before claiming PASS.**

### Trigger inventory (all 14 preexisting workflows)

| Workflow | Automatic event(s) before audit | Duplicates a single same-branch PR push? | Action |
| --- | --- | --- | --- |
| ci.yml, Rust checks + Python | unrestricted push **and** pull_request | **YES**; exactly the duplicate reported | Split and fix |
| classification-parity.yml | push main, paths; dispatch | No same feature-branch duplication | Unchanged |
| embedding-parity.yml | push main, paths; dispatch | No | Unchanged |
| full-audio-parity.yml | push main, paths; dispatch | No | Unchanged |
| mel-parity.yml | push main, paths; dispatch | No | Unchanged |
| resampler-diagnostics.yml | push main, paths; dispatch | No | Unchanged |
| genre-parity.yml | pull_request and push main, paths; dispatch | Normally no (feature PR vs main push) | Unchanged |
| voice-parity.yml | pull_request and push main, paths; dispatch | Normally no | Unchanged |
| windows-binary.yml | pull_request and push main, paths; dispatch | Normally no | Unchanged |
| model-smoke.yml | push any branch on src/Cargo changes; dispatch | No duplicate of itself; different test from Rust CI | Unchanged |
| deam-benchmark.yml | branch push of *its own workflow file*, dispatch | No | Unchanged |
| deam-mtg-overlap-audit.yml | branch push of *its own workflow file*, dispatch | No | Unchanged |
| fma-metadata-audit.yml | branch push of *its own workflow file*, dispatch | No | Unchanged |
| fma-genre-benchmark.yml | branch push of *its own workflow file*, dispatch | No | Unchanged |

Different workflows can still run for one commit because they test
different behavior; that is not duplicate execution of the same workflow.

### Changes

- `.github/workflows/ci.yml`: Rust-only `cargo fmt`, `cargo test`,
  `cargo clippy`. Triggered once by **push**, with Rust source,
  Cargo manifests/lock, build.rs and its own workflow file as path
  filters; optional manual `workflow_dispatch`.
- `.github/workflows/python-checks.yml`: existing Python tests on
  Linux and Windows and PowerShell AST checks, moved out of Rust CI.
  Triggered once by **push** on scripts/, tests/ or its own workflow
  file; optional manual dispatch.
- Documentation-only, README-only, or another benchmark workflow-file
  change does not run general Rust/Python CI. A scripts-only change
  runs Python CI but not Rust compilation; a src-only change runs
  Rust CI but not general Python CI. The dedicated parity/research
  workflows retain their own filters.

**Why push-only (not pull_request paths)?** GitHub evaluates
`pull_request.paths` against the *whole cumulative PR diff*, whereas
`push.paths` filters changed files in the pushed update. Our large
existing PR #16 already touches source and tests; a doc-only commit
would continue to run `pull_request` checks despite `paths` filtering.
See https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons.

**Trade-offs:** Push-only automatic CI covers branches *within this
repository* and records checks on head commits, but it does **not**
automatically validate pull requests whose head lives in a fork,
nor does it validate GitHub's synthetic PR merge commit. Use a
separate fork-safe `pull_request` workflow or manual dispatch if those
become requirements. Required-branch checks must be reviewed if path
filtering introduces missing required statuses. No change to branch
protection or repository settings was made.

### Workers and performance

The current DEAM and FMA benchmark scripts each loop over selected
audio IDs and invoke **one** `bliss-mood analyze-features` subprocess
at a time, with `--threads 1`. This limits ONNX intra-op threads,
not the number of parallel songs. Rust-v5 `scan-features` supports
`--workers`, `--adaptive-workers`, `--min-workers` and
`--max-workers`, but it requires a Bliss-style source catalog and
is **not called by these dataset benchmark scripts**.
The GitHub Actions `cargo build` itself is parallelized by Cargo,
subject to available runner CPUs; it is distinct from song analysis.

Optimization proposal, not yet enabled:

1. Preserve a known-good fixed serial baseline and compare the *same
   pinned songs* under sequential, two, and possibly three/four
   concurrent analysis processes (each `--threads 1`) on the same
   runner type. Record wall time, memory peak, track failures, features
   parity and all seven downstream metric values.
2. Avoid simultaneous SQLite schema creation/writes unless explicitly
   validated; prefer a bounded manifest-based Rust batch scanner
   reusing its validated scheduler, or independent worker sidecars
   merged and checked deterministically after analysis.
3. Do not blindly copy adaptive min_workers=4/max_workers=8
   from a larger workstation onto an Actions VM; those settings
   can oversubscribe limited CPUs and RAM. Compare fixed two workers
   versus adaptive only after safe orchestration exists.
4. FMA 7.2-GiB ZIP download and Rust build are large fixed overheads
   unaffected by analyzer worker count. Measure those stages
   separately; retain Cargo caching and source model hashes.

No claim of improved job duration or feature parity is warranted
without controlled GitHub Actions runs and actual results.
