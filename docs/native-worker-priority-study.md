# Windows scanner / original Essentia C++ worker priority control

**Status:** implemented in draft PR #18; qualification requires the green CI
checks **for the final commit** and a new Windows x64 artifact. This change does
not alter the class/mood/voice model weights, feature computation, original
Essentia C++ backend, existing song files or Bliss database.

## Prior measured confound: 27 October 2026, real 100-song NAS cohort

A controlled, bounded local 100-song native C++ benchmark completed two
repetitions of fixed 1/2/4/6 and adaptive 2–6 worker configurations. The local
report asserted **exact classification byte equality for all 300
song/head entries and complete 1280D embeddings**, with no failed scans.
Only aggregate statistics are retained below; private paths/song identities,
individual music files and private scanner logs are **not** committed.

| Mode | 2-run median wall seconds | 2-run median songs/min | Peak private process-tree MiB |
| --- | ---: | ---: | ---: |
| fixed 1 | 282.126 | 21.276 | not sampled in serial |
| fixed 2 | 277.649 | 21.950 | 226.922 |
| fixed 4 | 110.803 | 54.581 | 419.023 |
| fixed 6 | **93.417** | **65.144** | 657.281 |
| adaptive 2–6 | 116.852 | 51.367 | 552.539 |

Adaptive mode increased from **2 → 6 workers** through **four
adjustments per run**. The lower CPU utilization is not directly evidence
of Windows scheduler throttling: six parallel single-threaded inference jobs
cannot automatically saturate 16 logical CPUs; the pipeline also reads
music over the NAS, preprocesses audio and hashes files. A 20-second
controller cooldown and 24-completion minimum gate reduce early worker
admission. The two-run wall time is not enough to isolate those effects.

**Critical experimental confound:** previously `src/main.rs` lowered
Windows process priority to `BelowNormal` whenever `--workers auto` or
`--adaptive-workers` was enabled. Fixed numeric worker counts kept the
OS-assigned priority (normally `Normal`). Original Essentia subprocesses
are spawned without explicit priority flags, so Windows normally inherits
the parent's priority class. Earlier fixed/adaptive throughput numbers
therefore **do not isolate the adaptive controller**.

## New CLI behavior

`scan-features --priority normal|below-normal` sets the **Windows process
priority class** independent of `--workers`, `--workers auto` and
`--adaptive-workers`. The flag is **optional** and does not alter existing
behavior when omitted:

| Priority flag | Numeric fixed N | Auto or adaptive |
| --- | --- | --- |
| Omitted | Do not override OS-assigned class | Request `BelowNormal` (legacy) |
| `--priority normal` | Explicitly set `Normal` | Explicitly set `Normal` |
| `--priority below-normal` | Explicitly set `BelowNormal` | Explicitly set `BelowNormal` |

On **non-Windows platforms**, explicitly specifying `--priority` fails
with a clear error: mapping the Windows-specific priority class to POSIX
`nice` levels without an equivalent scheduling guarantee would be
misleading. Omitting it preserves the existing Linux/macOS behavior.
Dry-run does not modify the current process's priority.

Explicit Windows priority selection fails if `SetPriorityClass` fails
or if `GetPriorityClass` does not report the requested class. This is a
fail-closed experimental control; legacy implicit background priority
still warns on failure rather than silently changing the legacy exit
contract.

## Diagnostic contract

The `scan-features --json` output now contains a `priority` object
**also for a one-worker serial scan**, whose structure is:

```json
{
  "priority": {
    "requested": "normal",
    "policy": "normal",
    "effective_scanner": "normal",
    "native_worker_classes": ["normal"],
    "native_worker_observation_failures": 0
  }
}
```

`effective_scanner` is an actual Win32 `GetPriorityClass` reading,
not inferred from CLI arguments. The scanner reads `GetPriorityClass`
from each **original Essentia C++ child process handle immediately after
spawn**, stores its distinct observed classes, and reports the number
of failed queries. All launched children are included even if they exit
before the final scanner summary. An empty child array is expected
for the Rust audio backend or a scan with no new songs, but **is not**
accepted by the strict native benchmark. No child priority is guessed
from the parent's priority.

This is an OS process **scheduling priority**, *not* a CPU quota or an
affinity setting. It may affect latency under contention, but it
cannot be equated directly with the aggregate CPU utilization metric.

## Next comparison gate

`scripts/benchmark_native_adaptive_manifest.py` now passes
`--priority normal` by default to **every** fixed and adaptive scan.
It rejects any run for which `priority.effective_scanner` or the real
observed native child class is not exactly `normal`, and records
priority alongside timing and memory metrics in local `summary.json` /
`runs.csv`. Users may select `--scan-priority below-normal` to compare
at a second common priority, but **never mix two priorities within the
same five-mode fixed/adaptive experiment**.

The original 100-song private sample, official model files, native
worker and verified new Windows scanner artifact are reused.
The benchmark requires a *fresh, empty* output directory, does not
overwrite the original source DB or songs, and does not upload them.

Regression gates:

1. Rust CLI accepts valid explicit values independently of adaptive
   settings and rejects unrecognized or unsafe values.
2. Production priority resolution preserves the omitted-flag legacy
   policy on all platforms.
3. Windows native unit test sets both classes in a separate test process,
   launches an actual Win32 child and queries its **actual** priority
   to test inheritance. It does not alter priority in the parent CI
   test harness shared by other tests.
4. Python benchmark tests enforce `--priority` in every scanner command
   and reject mismatched/unobserved native worker priority.

This change alone **does not** prove priority is responsible for the
previous performance difference. Confirm the new scanner CI artifact
and reproduce the bounded local comparison before drawing that
conclusion.
