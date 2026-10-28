# Isolating ONNX inference in killable worker processes

**Status: design proposal (28 October 2026), not implemented.** This is the next safety boundary for experimental online autotune, after scan-local cancellation of native Essentia IPC and the experimental FFmpeg child. It must not change model evaluation, preprocessing, embedding sums, classifier scores, or SQLite storage semantics.

## Why cooperative checks are insufficient

Today each Rust worker thread owns an `ort::Session` for Discogs-EffNet and each selected Mood/Genre/Voice head. A RAM alarm sets a scan-local `Arc<AtomicBool>`, but a single `Session::run()` or `commit_from_file()` cannot be reliably preempted by Rust while ONNX Runtime holds memory. The old Rust audio decoder also blocked inside `ffprobe/ffmpeg .output()`; PR #19 now adds an opt-in supervised, bounded, cancellable subprocess path for that decoder. A 250-ms watchdog alone cannot guarantee against sudden allocations between samples, nor reclaim memory already held by an uninterruptible ONNX invocation.

A **killable process boundary** is the straightforward way to reclaim ORT memory when a scan exceeds its resource envelope. This is not yet a claim that out-of-memory events can always be prevented; the OS may terminate a process first. Also distinguish avoiding an OOM from handling a detected OOM cleanly.

## Proposed structure

```mermaid
flowchart TD
    A[Scan CLI / manifest / read-only audio root] --> C[Parent Rust coordinator]
    C --> G[CPU and RAM admission governor + watchdog]
    C --> D[Single SQLite sidecar writer]
    C --> T[Online throughput tuner]
    C --> P[Supervised Rust feature-worker process pool]
    G --> P
    T --> P
    P --> W1[Worker process: EffNet + ONNX heads]
    P --> W2[Worker process: EffNet + ONNX heads]
    W1 --> N1[Owned native Essentia C++ DSP child]
    W2 --> N2[Owned native Essentia C++ DSP child]
    W1 --> R[Bounded classification and optional 1280D embedding response]
    W2 --> R
    R --> C
```

The parent owns all sidecar writes, task selection and deduplication. Each worker process keeps its **own** persistent ONNX sessions and native DSP child; no ONNX environment is shared between worker processes. A worker can serve many songs. An admission-cap reduction stops new dispatch and lets old requests finish; a watchdog hard-stop kills the **entire supervised process subtree**, not only the Rust worker thread.

## IPC and resource contract

- **Versioned binary protocol** with a strict maximum frame length, request ID and exact selected model identity. Reject unknown protocol versions, excessive counts, malformed floats, truncated responses, duplicate completion IDs and outputs from the wrong worker/request. Use stdin/stdout pipes; keep diagnostics on stderr. Do not serialize/transport raw patch tensors or PCM across the parent-child boundary.
- One request contains sanitized track identity/source path, relevant validated model fingerprints and whether the optional pooled 1280D embedding is required. Parent validates the source root and read-only paths before dispatch; worker never opens Bliss/SQLite databases for writing.
- Worker response includes classifier scores and their labels/model keys (Mood/Genre/Voice), optional 1280D embedding, audio hash, patch count and per-stage timing. The parent is still the sole authority for atomic SQLite persistence. Preserve existing preprocessing/cache fingerprint versions unless **numerical parity** demands an explicitly versioned change.
- **Bounded IPC, outstanding requests and work:** only one in-flight task per worker process; no unbounded response queue; capped stderr, frame sizes and worker startup concurrency. Spawn workers lazily under resource admission. Run a short warmup outside scored probe windows.
- On timeout or memory fault, terminate the *owned* worker process tree and reap it; reject or flag all pending requests for that process as failed. Do not silently retry potentially changed audio. Never persist partial classification/embedding records. Abort the scan on memory-safety violation rather than success-with-missing-tracks.
- Windows: process Job Object with kill-on-job-close for worker plus descendants, retain a handle until confirmed exit. Linux: a supervised process group, with cgroup v2 containment when available; check PID-reuse safety and cgroup OOM events. macOS: verify process-group termination and RSS telemetry independently. Do not claim that merely dropping `std::process::Child` terminates descendants.
- Charge actual observed private/RSS memory and available RAM/cgroup headroom to the parent governor. Worker/child startup may temporarily double load and must fit the budget. Enforce host and process/cgroup CPU limits separately from throughput optimization. When telemetry is missing or inconsistent, fail closed in `autotune`.

## Migration boundaries

1. **First vertical slice:** add a hidden internal worker mode to the same Rust executable, with a framed, bounded handshake and one synthetic no-ONNX request/response. The default CLI behavior is unchanged. Test corrupt IPC, child crashes, hard hang, output caps, worker restart and concurrent independent scan cancellation. No `main` or SQLite DB changes in the worker.
2. **Extract the complete feature execution engine** into the internal worker: native Essentia C++ decoding plus shared EffNet inference plus selected heads, with optional embedding. Keep the parent as read-only source-selector and sole persistent writer. Maintain the current multi-head single-EffNet-pass algorithm and numerical order.
3. **Supervision/termination:** implement owned worker child/process-tree teardown on all targeted platforms. An injected simulated runaway ORT operation must be terminable without waiting for its runtime call to return. Exercise low-RAM cgroups and Windows Job Object behavior; do not rely on quick cancellation flags alone.
4. **Opt-in A/B parity:** identical private manifest/song metadata + model hashes, fixed same source bytes, compare all 56/87/2 classifier heads, 1280D pooled vectors, hash, model keys and patch counts against the existing native C++ frontend in **exact equivalence** where required. Do not publish local audio, private manifest or sidecars. Compare wall time, startup/idle resource overhead, process-tree private RAM, watchdog response and throughput at each candidate worker count.
5. **Only after the above pass:** let `--adaptive-policy autotune` select process-isolated feature workers. Keep `--adaptive-policy resource` and fixed workers compatible with their validated behavior until separately authorized to change them.

## Open design questions / measurable decisions

The parent will need to choose between prewarming workers and starting them on demand, including the cost of ONNX session allocations on a Raspberry Pi 4B. Consider a memory cost estimate **per selected model set** and observed peak per worker, instead of a universal fixed worker-memory estimate. The current online tuner uses complete-drain probe boundaries and forward/reverse repeated sweeps, but songs' patch counts do not fully normalize decode complexity or NAS load. Throughput optimization needs a measured *whole-scan* objective including startup and worker-transition overhead, and repeated/interleaved comparable song cohorts. Guardrail violations must take precedence over any throughput benefit.

## Related source

- `src/features.rs` — existing parent/worker-thread scan coordination and ONNX FeatureEngine.
- `src/essentia_worker.rs` — owned native C++ IPC child with existing cancel/reap behavior.
- `src/memory_watchdog.rs` — scan-local RAM watchdog and cancellation token.
- `src/audio_decode.rs` — supervised, cancelable FFmpeg/ffprobe path **only when an autotune cancellation token is provided**.
- `src/autotune.rs` — bounded RAM-gated nonmonotonic worker exploration.
- `docs/online-autotune-phase-b.md` — current Phase B implementation and verification limits.
