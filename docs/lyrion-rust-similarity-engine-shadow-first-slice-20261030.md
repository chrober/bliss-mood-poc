# Lyrion General Similarity Engine: first real Rust-to-sidecar research slice (30 October 2026)

> **MIGRATION NOW HAS A SEPARATE OWNER:** This prior first-slice document describes the 30-Oct in-research prototype. Its actively developed successor is [`chrober/essentia-similarity` PR #1](https://github.com/chrober/essentia-similarity/pull/1): host-neutral scorer, independently reusable feature store and CLI; [Linux/Windows CI PASS](https://github.com/chrober/essentia-similarity/actions/runs/41090809405). The prototype remains a reproducibility artifact, **not the target SPI v2 provider or general production runtime**. Separate native and LMS guidance plugin contracts were created as draft [native PR](https://github.com/chrober/bliss-guidance-essentia/pull/1) / [Lyrion PR](https://github.com/chrober/lms-guidance-essentia/pull/1). No actual plugin or active product feature exists. See [cross-repo migration handover](essentia-similarity-cross-repository-migration-20261030.md).


**Scope:** Isolated research branch only. [Approved product architecture and owner map](lyrion-research-to-product-integration-decision-20261030.md). This implements a **reusable Rust geometry library** and a genuinely executable **read-only SQLite v3 shadow CLI** sharing the scanner's *existing* strict feature lookup. It is **not** an installed Guidance SPI v2 plugin, candidate retriever, production General Metric, Better Call Bliss optimizer integration or playlist reranker.

## 1. Artifacts and existing code reused

| Component | Actual function | Boundary |
| --- | --- | --- |
| [Standalone Rust crate](../research/lyrion-similarity-engine/Cargo.toml) | Independently importable `lyrion_similarity_engine_research` library and separate `lyrion-similarity-shadow` CLI | No LMS, audio playback, ONNX, training or personal state in geometry library |
| [Core geometry](../research/lyrion-similarity-engine/src/lib.rs) | Versioned `affine_cosine_v1` / `affine_centered_cosine_v1` for sigmoid Genre87 and Mood56; strict finite inputs, nonconstant vector condition, dimensional parity, symmetric higher-is-more-similar score in [0,1] | **Geometric proxy only, not perceptually calibrated**. No General/PERSONAL fusion, no model chosen |
| [Read-only sidecar adapter and CLI](../research/lyrion-similarity-engine/src/bin/shadow.rs) | Checks trusted full candidate pool and queries the **actual scanner** feature v3 table by exact host-supplied `track_file` keys; returns only anonymous whole-query shadow rank statistics | Never modifies source DB, original `bliss.db`, routes or queues; no source audio or neural inference |
| [Existing scanner accessor](../src/feature_lookup.rs) | Reuses `inspect` and its `SQLITE_OPEN_READ_ONLY` connection; `PRAGMA user_version=3`, `feature_tracks`/ `feature_models`, vector validation, model labels and `validated_against_essentia` | Linked as source via Rust `#[path]` in the research binary; **no duplicate SQL decoder** and no rewrite of scanner module |
| [Linux/Windows research CI](../.github/workflows/research-lyrion-rust-similarity-engine.yml) | Standalone Cargo library and binary tests, actual temporary SQLite v3 content, formatting of isolated Rust crate | Not a deployed Pi benchmark or Lyrion native plugin integration |

**Why two parts:** Geometry should be reusable by a future plugin-owned Guidance SPI v2 provider and, later, a native feature-first/hybrid candidate source. The sidecar/host identity adapter is separate; it should not make the scoring library depend on Lyrion, filename conventions or SQLite. Currently the *binary* reuses the in-repository scanner accessor via a relative Rust source path; before independent publication move that lookup behind a stable separate crate/API rather than copying it.

## 2. Trusted local shadow request contract (example)

Run only with a **trusted locally generated** JSON file; `feature_database` must be fixed by trusted integration settings and NEVER accepted from a web form, untrusted candidate, or arbitrary SPI `score` payload. Candidate file identities and ranks must originate from the verified Bliss admission host, not artist/title heuristics:

```json
{
  "schema": "lyrion-general-sidecar-shadow-v1",
  "mode": "shadow_only",
  "feature_database": "/absolute/trusted/path/to/mood.db",
  "anchor_track_file": "Artist/Album/seed.flac",
  "model_id": "genre",
  "metric": "affine_centered_cosine_v1",
  "expected_model_key": "specific-actual-feature-model-fingerprint",
  "experimental_preview_opt_in": false,
  "candidates": [
    {
      "candidate_id": "original-bliss-candidate-identity-1",
      "track_file": "Artist/Album/candidate-one.flac",
      "bliss_rank": 0,
      "admitted_by_bliss": true
    },
    {
      "candidate_id": "original-bliss-candidate-identity-2",
      "track_file": "Artist/Album/candidate-two.flac",
      "bliss_rank": 1,
      "admitted_by_bliss": true
    }
  ]
}
```

```bash
cargo test --manifest-path research/lyrion-similarity-engine/Cargo.toml --all-targets
cargo run --manifest-path research/lyrion-similarity-engine/Cargo.toml --bin lyrion-similarity-shadow -- --request /local/trusted/shadow-request.json
```

This is **an API contract/example, not a request to create a user's live file or activate guidance**. It requires a real local feature SQLite sidecar and exact matching model key; an unset/malformed/nonexistent source yields a neutral result, not fake music scores. The two-songs minimum and 50-candidate maximum match the bounded exploratory comparison, not arbitrary global corpus retrieval. The request explicitly **cannot instruct the CLI to publish the proposed order or modify a route**.

The only supported current `model_id` values are `genre` (87D) and `moodtheme` (56D). The independently researched 1280D embedding is **not** presented as available in the current generic feature SQLite v3 rows; a separately validated embedding storage/identity contract is required before adding it. `affine_centered_cosine_v1` mean-centers **each input vector independently** exactly like `scripts/evaluate_similarity.py`, **not** a fit on the candidate pool. Both provisional methods emit `(1 + clipped_cosine) / 2`. This is a ranking-oriented fixed geometric mapping, **NOT** evidence that Genre, Mood, Embedding, Personal or raw Bliss scores have comparable calibrated scales.

## 3. Fail-closed behavior, no false joins

- Input must be `shadow_only`, explicit schema version, exactly one of the supported heads, a supported metric name and a nonempty expected model fingerprint. Unknown JSON fields and non-Bliss-admitted, repeated, empty, NUL-containing or nonconsecutive rank requests are rejected before any SQLite lookup.
- All candidate file keys and the anchor must be exact original `TracksV2.File` values. The current Lab SPI provider adapter has `lms_urlmd5` / candidate IDs; a guaranteed `urlmd5` → exact `TracksV2.File` resolver is **NOT YET implemented**. This CLI does not synthesize it or use `rowid` as external identity.
- A missing, stale or unreadable source, wrong v3 schema, missing head, invalid vector, model fingerprint mismatch, unvalidated input, any degenerate geometry or incomplete pool gives a **neutral whole-query fallback**. No rank replacement; no per-candidate boost only for the available subset. The original Bliss output remains valid.
- `experimental_preview_opt_in=false` defaults to forbidding any feature with `validated_against_essentia=0`. If true, those feature rows can be used for **research shadow statistics only**, never as production guidance.
- The output reports `candidate_count`, `status`, bounded failure **reason codes**, `changed_positions`, `top5_overlap`, and `max_absolute_rank_shift`. It never emits individual songs, artist names, source paths, embeddings, personal labels, selected candidate IDs or scores.
- The geometry library and CLI do not create a playlist, queue, route or provider process and do not call any Lyrion API. A standalone reported rank change proves **only that the formula could change a ranking**, never that it improves musical listening.

## 4. Exact near-term integration work (not yet implemented)

1. **Host-owned identity join P1:** add a trustworthy source-key resolver in the Lab host flow from its known LMS track references to exact Bliss `TracksV2.File`, including Unicode, multiple music roots, CUE suffixes and ambiguous/missing paths. Verify on bounded read-only tracks and compare against original Bliss; do NOT match by names or silent path replacements.
2. **Read-only model-coverage probe P1:** freeze a real sidecar version/model fingerprint and read-only single invocation. Verify actual source-file and class/fingerprint parity. The scanner's prior fixture parity does not automatically mark real song features validated.
3. **Actual Lab-only shadow bridge P2:** invoke this library/adapter with a **frozen already-admitted Bliss pool**, preserving originals. An existing SPI v2 interface handles optional providers via `describe/prepare/score/close`. **Implementing that wire lifecycle and plugin packaging is an explicit separate engineering task**; this CLI is deliberately not an SPI endpoint or a substitute for its formal protocol. The provider should handle trusted local sidecar paths and bounded batches without relying on browser-supplied executables/files.
4. **Live opt-in A/B P3:** only if WP1 selects/validates a General Metric and licensed locally generated feature provenance is complete. Host owns bounded combination, actual selection, repeat/genre/virtual-library rules and neutral fallback, with measured Pi performance and accepted listening/recommendation targets.
5. **Better Call Bliss P4:** reuse the same core/provider but separately verify contextual *directed* transition scoring and whole-route feasibility; no direct playlist write before user approval. **Feature-first/hybrid P5** requires a *new host-owned candidate retrieval* contract, not SPI provider expansion.
6. **Personal P6:** once real independent personalization quality and calibration gates pass, blend independently versioned General/Personal scores with 0–100% influence and full-query general fallback. This is distinct from Lab's current 23D Bliss `learnedblend`.

## 5. Evidence and restrictions remain unchanged

Original MTT 193/293 majority-decisive triplet results and locally rated 11-pair listener pilot are exploratory; CCMSim third-party model Spearman is not a measurement of our scorer; 1280D mood/genre vs embedding representation remains unresolved. WP2 synthetic Personal Metric tests, WP3 teacher-approximation failure/low correlation, missing real-audio independent General quality tests, source licensing restrictions, official FMA TEST freeze and original MTT 7/30 audio-source blocker all remain in force.

**No `main`, draft PR #16, existing Lyrion installations, BlissMixerLab, Better Call Bliss, Bliss core `bliss.db`, or user files were changed.** The research crate and its own CI are independently testable but have not been shipped as a product plugin.
