# Chat handover — adaptive offline feature scans (2026-10-19)

> **Purpose:** Start a new development chat without losing the current project
> state. The detailed performance experiment, raw benchmark measurements,
> implementation details and open questions are in
> [adaptive-scan-performance-handover.md](adaptive-scan-performance-handover.md).
>
> **Source of truth:** Always re-check current GitHub \`main\` before making
> claims or changing code. This handover was prepared against
> \`55b35dab1a873c3e61ecd639b7430caf0b09034c\` (PR #5 merged), before the
> documentation-only handover PR. Do not assume that SHA is still the latest.

## Project and boundaries

Repository: [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc).
Experimental Rust/ONNX offline audio analysis to complement Lyrion/Bliss,
**not** an instruction to change production mixers, plugins or Bliss Guidance
SPI. The generic CLI handles **three independent heads** sharing one
Discogs-EffNet embedding per song:

- \`moodtheme\` — 56-label MTG-Jamendo Mood/Theme (Sigmoid).
- \`genre\` — 87-label MTG-Jamendo Genre (Sigmoid).
- \`voice\` — Voice/Instrumental, 2 labels (Softmax). Not vocal-technique or
  percentage-of-vocal-time detection.

Original \`bliss.db\` and audio are read-only. Experimental results live in a
separate SQLite sidecar, schema v3, keyed by exact \`TracksV2.File\` identity.
Old Mood-only CLI and legacy rows remain untouched. Real-world prediction
quality is **not** production-validated; verified synthetic Essentia numerical
parity is not evidence of musical usefulness. See
[feature-provider-architecture.md](feature-provider-architecture.md) and
[offline-mood-database.md](offline-mood-database.md).

## What has shipped

1. Generic Mood + Genre + Voice analysis, shared encoder, model registry,
   per-head caching and validated numerical parity.
2. Incremental \`scan-features\` with bounded, parallel *songs*, independent
   per-worker ONNX Sessions and a single transaction-safe SQLite writer.
3. Corrected ONNX Runtime process-global Environment (earlier concurrent
   \`ort::init().build()\` attempts failed on Windows).
4. \`--max-new N\` means **at most N newly attempted tracks**, not N
   successes; \`--max-errors N\` aborts repeatedly failing scans.
5. \`--workers auto\` keeps Windows responsive (roughly 25% CPU headroom,
   cap eight), \`--workers N\` is explicit; for parallel use \`--threads 1\`.
6. [PR #5](https://github.com/chrober/bliss-mood-poc/pull/5), merged:
   opt-in \`--adaptive-workers\` with \`--workers 6 --min-workers 4
   --max-workers 8\`; per-song decode/preprocessing/inference/hash/load
   stage totals; OS CPU/RAM monitoring; logged worker adjustments.
   The fixed-worker interface remains available and unchanged.

Important source entry points:

- \`src/features.rs\`: \`FeatureEngine\`, \`scan_parallel\`,
  \`save_completion\`, \`ScanSummary\`, \`ScanDiagnostics\`.
- \`src/parallel.rs\`: \`worker_count\`, \`AdaptiveWorkers::observe\`.
- \`src/resources.rs\`: OS-level load sampling.
- \`src/main.rs\`: CLI flags and validation.
- \`src/storage.rs\`: read-only upstream Bliss access and SQLite sidecar.
- \`model-registry.json\` and
  \`.github/workflows/voice-parity.yml\`: model contract and integration tests.
- \`README.md\`: usage and caveats.

## Real test setup

User machine: Windows 11, HP Laptop 15-fc0xxx, AMD Ryzen 7 7730U,
8 physical cores / 16 logical CPUs, ~16 GB physical RAM; Wi-Fi 6 Realtek
RTL8852BE-VS at negotiated 600 Mbit/s. Music on NAS UNC share
\`\\192.168.1.100\music\`, local checkout
\`D:\LMS\bliss-mood-poc\`, 64,062 eligible Bliss tracks.

Deterministic local 100-song fixture:
\`D:\LMS\bliss-mood-poc\benchmark-workers-20261019-060347\sample-100.db\`
(seed 20261018). Benchmark sidecars:
\`features-6.db\`, \`features-8.db\`, \`features-10.db\`,
\`features-12.db\`; raw samples \`resources-*.csv\`, \`summary.csv\`
and \`summary-with-6.csv\`. Keep this suite for apples-to-apples work;
do **not** upload personal music or database to GitHub.

**Fixed-worker results over the same 100 tracks**:

| Workers | Wall time | Songs/min | System CPU avg | RAM max | Analyzer RAM max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 80.48 s | 74.6 | 47.9% | 85.0% | 0.66 GB |
| 8 | 80.18 s | 74.8 | 63.5% | 89.5% | 1.17 GB |
| 10 | 82.29 s | 72.9 | 70.8% | 91.6% | 1.94 GB |
| 12 | 112.79 s | 53.2 | 83.2% | 97.5% | 3.21 GB |

All 300 model vectors per run were **byte-identical**. With six workers:
CPU max 87%, WLAN receive mean 24.05 MiB/s, max 39.08 MiB/s. Six fixed
workers are the measured efficiency baseline; eight have similar throughput
at much higher resource pressure.

**First adaptive run**, reported after PR #5 from a database within the
same benchmark directory:
\`adaptive-20261019-080350.db\`; 100/100 successful, zero failures,
**120.66 s (49.7 songs/min)**; workers initial/final/max **6/6/6**,
CPU avg 51.26%, peak RAM 86.33%, 38 OS-load samples, **no adjustments**.
Per-song *summed overlapping* durations: decoding 173.52 s, Mel/patches
100.82 s, ONNX 343.09 s, SHA-256 reread 66.54 s, session init 1.63 s,
sum of song durations 685.61 s. These are NOT sequential wall-clock or
exclusive CPU durations.

The adaptive controller's low-load rule is **CPU <=65% AND RAM <=79%
for 3 consecutive resource observations**. High-load rule is **CPU >=90%
OR RAM >=88% for 2 consecutive observations**. Changes are inhibited
until >=24 completed songs and at least 20 s since the last adjustment
(or creation). The observed near-86% RAM can sit in the deadband for the
entire run. Therefore **no worker change is not proof of a bug**. The
report shows only maximum RAM, not every sample: inspect actual timelines
and effective conditions before concluding why no adjustment occurred.
Whether the ~50% longer adaptive runtime is reproducible, and whether
the command truly used an identical track set/cache/priority, remain OPEN.

## Next work — priority order

1. **Investigate the adaptive performance regression** on exactly the
   existing \`sample-100.db\` and music source. Compare fixed six vs adaptive
   six under equivalent environment and process priority; alternate run
   order/repeat measurements, inspect NAS/OS caching, thermal/power throttling,
   and runtime phases. Do not conclude adaptive scheduling is at fault merely
   because of one timing difference.
2. **Make decisions explainable**: record per-resource sample time, CPU/RAM,
   consecutive low/high counters, cooldown, controller state, real in-flight
   count and why it held or changed. Check for starvation caused by samples
   only being taken when job results arrive.
3. **Evaluate safe policy options**, with tests: explicit pressure-only guard
   (reduce at high RAM/CPU), separate throughput-seeking tuning policy, or
   thresholds based on available memory + CPU/queue throughput rather than
   CPU/RAM fixed cutoffs alone. A correct policy may intentionally stay at six.
   Do not blindly force an adjustment.
4. **Measure NAS versus local SSD** on identical files with controlled
   cache state; distinguish SMB latency, network throughput and CPU
   preprocessing/inference. File hashing reads the source twice overall.
5. Regression CI: deterministic simulated resource timelines (high, low,
   deadband, missing samples, cooldown); verify real in-flight changes,
   maximum attempts, error stop and byte-identical feature vectors.
6. Only after evidence, optimize the controller and maybe expose explicit
   \`--max-workers\` defaults; keep fixed-worker behavior stable. Later:
   full-library progress/ETA and resumable/interruptible UX.

## Rules for the next chat

- Fetch fresh \`main\` SHA and review these docs + source **first**.
- Diagnose rather than assert adaptive is broken: 6/6/6 can be correct.
- Prefer a reproducible minimal PR; run Rust tests, Clippy, Windows x64,
  and required Essentia/model parity before merge.
- No production mixer/plugin changes. Keep \`bliss.db\`/music read-only;
  new SQLite benchmark DBs only; never commit music, model weights,
  local sidecar DBs or personal track lists.
- Always bound experiments: \`--max-new\`, \`--max-errors\`, timeouts;
  \`--threads 1\` when parallel. Retain \`--workers N\` and
  \`--adaptive-workers\` as optional.
- The user prefers actionable full PowerShell blocks (\`& { ... }\`) and
  measured evidence over speculative optimizations.
