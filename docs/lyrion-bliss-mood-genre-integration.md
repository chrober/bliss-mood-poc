# Bliss + Mood/Genre fusion for Lyrion — integration workstream

**Status (2026-10-19):** Architecture/implementation handover; **not yet
deployed**. This is the current product priority, ahead of scanner
performance and the deferred [platform-resource roadmap](platform-resource-roadmap.md).

## Target user experience

Keep the upstream Bliss Mixer functional and unchanged. Let a user opt into
an experimental **Bliss + Mood/Genre** strategy through a separately
installed Lyrion extension, initially Bliss Mixer Lab. The output is still
a Lyrion playlist / DSTM queue obeying existing candidate eligibility,
artist/repeat constraints, virtual library and source restrictions.
Two independent influence settings govern Genre and Mood/Theme (default 0),
with a visible Bliss-only A/B fallback.

The intended use is *better musical coherence and intentional movement*
between songs, not changing acoustic-feature analysis or replacing the
Bliss analysis itself. Final product evaluation must use real music and
listening feedback in addition to numerical tests.

## Grounded current state

- Upstream Bliss Mixer owns its existing acoustic database `bliss.db`,
  its source files, and original mixing rules; read-only consumers never
  write or rewrite them.
- `bliss-mood-poc` can produce a separate SQLite schema v3 database with
  `feature_tracks` and `feature_models` for independent per-track
  `moodtheme` (56 Sigmoid) and `genre` (87 Sigmoid), optionally
  `voice` (2 Softmax). All heads share a Discogs-EffNet 1280D encoder
  during offline inference. No inference should occur during mix creation.
- `feature_tracks` uses **the exact original `TracksV2.File` key** and
  a per-model fingerprint. Floating vectors must be decoded according to
  the ordered `classes_json` stored with their model fingerprint:
  IEEE-754 float32 little-endian. Do **not** use Bliss's `rowid` as a
  cross-database identifier and do not match by artist/title.
- `chrober/lms-blissmixer-lab` already provides a separate Bliss-first
  candidate pool and is a Lyrion host for optional guidance providers;
  it can invoke native JSONL SPI v2 providers via its shared host.
- `chrober/bliss-playlist-guidance-spi` permits bounded reranking of
  an **existing** Bliss-qualified shortlist. SPI v2 candidate and anchor
  schema already includes optional `database_file`, but current Lab
  provider adapters may populate only `candidate_id` and
  `lms_urlmd5`, and sometimes `database_file: null`.
  **The canonical file-key join must be implemented and tested**, not
  assumed to work merely because the schema has the field.
- Inference parity on synthetic fixtures is not a real-music validation.
  The stored `validated_against_essentia` flag is currently false.
  Production consumers must ignore such vectors by default.
  A **clearly marked experimental Lab-only preview** may deliberately
  opt into inspecting unvalidated results without relabeling them validated
  or silently activating them in production mixes.

Reference repos:
[chrober/lms-blissmixer-lab](https://github.com/chrober/lms-blissmixer-lab),
[chrober/bliss-playlist-guidance-spi](https://github.com/chrober/bliss-playlist-guidance-spi),
[chrober/lms-guidance-library-signals](https://github.com/chrober/lms-guidance-library-signals),
[chrober/bliss-guidance-library-signals](https://github.com/chrober/bliss-guidance-library-signals).

## Explicit separation of three responsibilities

| Role | Owner / initial integration |
| --- | --- |
| Feature production | Offline `bliss-mood-poc scan-features`; separate schema-v3 feature SQLite sidecar |
| Candidate admission / hard constraints | Existing Bliss Mixer / BlissMixerLab, unchanged in first release |
| Guidance and final choice | New optional Mood/Genre guidance source via existing SPI v2; Lab combines bounded signals with its other providers and owns playlist/queue |

### First strategy: Bliss-first + Mood/Genre reranking

1. Lyrion/Bliss Mixer Lab acquires its usual bounded Bliss candidate pool.
2. The host resolves **exact** per-track Bliss keys for seed/context tracks
   and candidates. Any unresolved mapping gives **neutral** guidance.
   Avoid inventing or guessing file roots in the native provider.
3. The new feature guidance provider opens a *trusted*, locally configured
   **read-only** schema-v3 SQLite sidecar. It verifies schema, model key,
   class ordering, vector size/ranges/finiteness and validation policy.
   Reuse one SQLite connection/snapshot per invocation; query only
   requested seeds and bounded shortlist, no full-library read or ONNX.
4. Compute Genre and Mood similarity **separately**, only between compatible
   same-head vectors from the same model/preprocessing fingerprint and label
   ordering. Handle near-zero vectors, degenerate/uniform scores, missing
   anchors/candidates and different taxonomies as **neutral**; do not
   average scores between heads directly.
5. Produce separately bounded `genre` and `mood_theme` SPI v2 guidance
   channels (signed [-1, 1], confidence [0, 1]). The host performs any
   calibrated shortlist normalization and weighted combination with Bliss,
   not the provider. Host influences are separately user-controlled, default
   to 0, and can be disabled independently. Neutral configuration must
   reproduce the existing Bliss order.
6. Preserve Bliss eligibility: the provider may **only re-rank**
   admitted tracks and cannot add tracks, bypass repeat/genre constraints,
   or force a new route. Timeout, malformed sidecar, missing data or
   provider failure must leave a valid Bliss-only mix.

The first product target is a Lab-only A/B preview. Do not enable provider
by default. Full native Lyrion plugin packaging and actual Pi binary
execution are separate verification gates.

### Later, not part of the first bridge

- **Feature-first:** mood/genre retrieves candidates outside Bliss's
  acoustic shortlist, followed by Bliss transition scoring. The current
  SPI v2 cannot do this; it needs a new host-owned candidate-source contract.
- **Hybrid:** explicit union of Bliss and feature candidate sources with
  coherent normalization, provenance, fallback and musical drift control.
  Must preserve all existing Lyrion hard filters.
- A user-requested genre journey/mood trajectory and fixed
  source-identity drift anchors are separate future policy controls.
- Voice is already analyzed but is not required for the first Mood+Genre
  blending experiment; singing style is not inferred by the Voice head.

## First implementation slices and acceptance criteria

### F1 — Sidecar inspection and exact identity contract (first coding slice)

In the **feature analyzer repository** provide a small read-only inspection
path or fixture/API for selecting `moodtheme` and `genre` vectors by exact
`track_file`, with correct model metadata and provenance. Synthetic
fixtures must establish: existing/missing track, both heads, only one
head, incompatible model fingerprints, invalid/malformed vector, zero
vector, and unavailable sidecar. This is **not** a fresh ONNX scan or a
change to the schema.

In the Lab integration, verify with a representative frozen set of Lyrion
tracks that `candidate_id` / `lms_urlmd5` can be mapped unambiguously to
the exact Bliss `TracksV2.File` key. If not, make the adapter supply the
explicit `database_file` field from a verified source (including seed
anchors), with regression tests. No artist/title guessing, no rowid join,
no implicit path normalization.

**Gate:** given a known seed and a bounded candidate batch, the system
fetches only the expected vectors and correctly reports missingness and
validation status without touching `bliss.db` or audio files.

### F2 — Native, provider-neutral scoring prototype

Implement a small read-only native Mood/Genre SPI v2 JSONL provider
(new dedicated provider project preferred rather than putting mixer
policy into the scanner). Support `describe`, `prepare`, `score`,
`close`, a trusted feature-SQLite resource kind and independently
bounded per-head channels. Provide deterministic fixtures for:
equal vs dissimilar vectors, single missing head, mixed fingerprints,
disabled/zero influence, corrupted SQLite, timeout and neutral failures.
Do not spawn FFmpeg or ONNX at mixing time.

**Gate:** frozen Bliss candidate batch + seed => per-channel signals
with provenance and strict bounds; missing/invalid data yields neutral
fallback and no new candidate.

### F3 — Experimental Lyrion plugin + Lab host wiring

Implement a separately installable passive Lyrion plugin using existing
guidance provider kit conventions (descriptor/defaults/status/native SPI
configuration/settings), discoverable from Lab and off by default.
Use a trusted configured feature-sidecar path, never a path originating
from a playlist request. Follow the existing Lab deadline and process
handling. The host renders concise diagnostics for number of covered
tracks, missing anchors, fingerprint mismatch, and contributions.
Do not modify production upstream Bliss Mixer.

**Gate:** a reproducible Bliss-only vs Bliss+Genre vs Bliss+Mood vs
combined preview on the same frozen seed/candidate set, with existing
hard constraints and failure fallbacks unchanged.

### F4 — Musical evaluation and safe release gates

Collect a representative real-music set including ambiguous multi-genre
tracks, closely related genres, large mood shifts, long intros, and
duplicates. Review the actual 56/87 scores against the user's judgement
and, where possible, independent Essentia full-track references. Record
subjective results and validate the provenance flag accurately.
Run performance checks on real Pi/Lyrion later; a Linux ARM64 CI build
alone is not proof of piCorePlayer ABI/runtime compatibility.
Release only with opt-in controls, working fallback, source licensing review
and no production use of unvalidated vectors by default.

## Immediate work order

**Next engineering task: F1.** Establish the exact Lyrion-to-Bliss
`track_file` join and a tested, read-only extraction of Mood/Genre
vectors from schema-v3 SQLite. This is the critical integration seam;
changing the scanner's number of workers is not required.

**Deferred:** [platform resource architecture](platform-resource-roadmap.md).
Read [chat-handover.md](chat-handover.md) for repository/CI rules; Windows
Rust binaries are built by PR-triggered GitHub Actions, **never locally**.


## F1 first implementation — read-only feature lookup CLI

A focused F1 code slice adds `bliss-mood inspect-features` for existing
schema-v3 sidecars. A bounded repeated `--track-key` list uses the exact
`TracksV2.File` values and returns independently typed Mood/Genre
`model_key`, label order, preprocessing and aggregation metadata,
validation flags and scores (only when permitted). It never scans media,
invokes ONNX, creates a database or writes to the source sidecar.

Example (replace the executable with the verified Actions artifact):

```powershell
& {
    $exe = 'PATH-TO-VERIFIED-GITHUB-ACTIONS-EXE'
    & $exe inspect-features --db .\mood.db --track-key 'Artist/Album/track.flac' `
        --models moodtheme,genre --json
    # In an isolated Lab preview, append --include-experimental to reveal
    # unvalidated predictions. The default emits no such score vectors.
}
```

Read-only lookup is a **diagnostic/contract first step**, not a deployed
Guidance SPI provider. Next task: host-side exact-key mapping for LMS
anchors/candidates, followed by a separate SPI v2 provider. Do not imply
that the extractor already reranks Lyrion tracks.


## F2 proof-of-concept: native SPI v2 Mood/Genre scoring

**Status:** Experimental standalone binary only; not installed or enabled in Lyrion.
The repository now also contains \`src/bin/bliss-feature-guidance.rs\`, a
separate passive JSONL SPI v2 process. It receives a *trusted* read-only
schema-v3 \`bliss-feature-sqlite-v3\` resource in \`prepare\`, resolves seed
\`anchor_id\`s and candidate \`database_file\` keys, and returns
independent \`genre\` and \`mood_theme\` bounded-influence signals.

The standalone scorer never generates new candidates, writes SQLite or
\`bliss.db\`, decodes audio, or invokes ONNX. Only matched model fingerprints,
correct dimensions (87/56), identical aggregation, nondegenerate 0..1
vectors and validated content produce normal scores. The trusted Lab-only
\`include_experimental: true\` option is required for the currently
unvalidated vectors; by default those inputs cause neutral/no signals.

Initial similarity is deliberately **provisional**, not a calibrated
musical-distance metric: independent per-head
\`1 - 2 * RMS(seed-vector - candidate-vector)\`, bounded to [-1,1].
Missing or incompatible anchors/candidates yield **no** signal. Multiple
eligible context anchors contribute an average per head. The Lyrion host
owns settings, bounded influence, candidate selection, and fallback.

The Windows x64 GitHub Actions artifact now also contains
\`bliss-feature-guidance.exe\` with a checksum. This is a testing tool,
not a production Lyrion plugin. The current Lab repository is readable but
the connected GitHub integration returned HTTP **403** when asked to
create a feature branch, so no changes to \`lms-blissmixer-lab\` have been
made or claimed. Host-side exact \`database_file\` identity mapping and
separate plugin packaging remain necessary.

For an isolated contract exercise, send the following **one JSON object per
line** (using an actual existing sidecar path and exact track keys):

\`\`\`json
{"type":"describe","spi_version":2}
{"type":"prepare","spi_version":2,"job_id":"lab-preview","options":{"include_experimental":true},"artifacts":[],"resources":[{"kind":"bliss-feature-sqlite-v3","path":"C:\\\\temp\\\\mood.db","access":"read_only"}],"anchors":[{"anchor_id":"seed1","candidate_id":"lms-seed","database_file":"Artist/Seed.flac"}]}
{"type":"score","spi_version":2,"request_id":"preview1","context":{"scope":"global","context_track_ids":["seed1"]},"candidates":[{"candidate_id":"bliss-candidate-1","database_file":"Artist/Another.flac"}]}
{"type":"close","spi_version":2}
\`\`\`

**Next:** obtain write access to Lab, implement and test the canonical
Lyrion-to-Bliss track key join for both anchors and candidates, then expose
this scorer through a passive provider plugin and Lab's existing host
contracts. Keep legacy provider logs and existing mixing unchanged until
a documented A/B preview passes.
