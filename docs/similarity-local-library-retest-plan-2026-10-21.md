# Lyrion — next local song-representation listening comparison

**Status:** October 21, 2026; planning document. **No new local test has started.**
Work only on `feat/similarity-metric-evaluation` / Draft PR #16.
Do not change `main`, PR #13/#17, the production mixer, or user audio.

## Why do we need a local listening study after FMA, MTT, and DEAM?

Neither the FMA coarse-genre retrieval test nor the completely explored
MagnaTagATune triplet questions demonstrate that the current raw 1280D
embedding is a universal winner. DEAM's valence/arousal proximity is
not direct human judgment of how tracks follow one another in a playlist.
The paired DEAM A/B comparison remains blocked by the official archive
host's intermittent/unavailable HTTPS endpoint.

The initial real Lyrion listening pilot rated **eight pairs**:
**zero positive and eight negative Genre judgments**, plus four
positive and four negative Mood judgments. There is not enough
positive Genre coverage for an ROC-AUC and nowhere near enough
evidence for a production method. Refer to the
[listening review handover](similarity-listening-review-handover-2026-10-21.md).

## Small, separately verified steps — no full-library scan

**L0 — local read-only inventory; no new ratings.**
Select a bounded, already analyzed set of songs with exact file-key
mapping. Inspect schema-v3 SQLite track keys, audio SHA, the 87D Genre
and 56D Mood model/preprocessing fingerprints, class ordering, and
patch counts. Look for a separate versioned 1280D song-embedding
sidecar **for exactly those same tracks**. Do not assume that running
the 1280D encoder implicitly saved a pooled song vector.
**Do not scan the entire library, upload a private cache, or overwrite
existing SQLite feature rows.** If embeddings are absent, plan a
limited, separate research CLI export without porting changes
from PR #17 or changing the mixer.

**L1 — approximately 12 new listening contrasts.**
Use the same seed tracks and audio for every candidate method,
with fixed randomized presentation order:

- Around four independently human-identified stylistically similar
  pairs as positive controls; avoid repeating the pilot's all-negative
  Genre class.
- Around four clearly different Genre/Mood pairs as negative controls.
- Around four hard comparisons on which raw embedding cosine and
  classification-based similarity make substantially different
  predictions. **These are model-selected diagnostic challenges,
  not an independent representative test set.**
- Hide method names, scores, ranking, and selection stratum while
  listening. Song/artist names may be visible to find personal recordings.
  Randomize left/right presentation; never infer labels from track names,
  ONNX activations, or inferred metadata.

**L2 — human evaluation.**
Rate each contrast independently on **four axes**:
(1) stylistic/Genre similarity, (2) Mood/energy proximity,
(3) audible/timbral similarity, and (4) suitability as an immediate
playlist successor. A 1–5 scale can be used for each axis, with
a separate cannot-assess option. Optionally capture confidence
(1–3) and a note. Do not collapse the dimensions into a single
supposedly objective similarity target. Preserve the original
eight pilot labels verbatim.

**L3 — read-only scoring and review.**
Calculate Genre Cosine/Centered Cosine, Mood Cosine/Centered Cosine,
and 1280D Audio Cosine for **the same song pairs and anchors**,
including undefined-score counts, shared coverage, difficult
negatives, human axes, small-sample limitations, and selection bias.
Do not declare statistical superiority or deployment readiness
from only 12 new contrasts. A predefined constant-weight fusion
could be shown only as exploratory; do not tune fusion weights to
the same human labels.

After this instrument pilot, decide whether to freeze a **fresh,
previously unseen 24–40-pair evaluation block**, attempting song,
album, and artist group separation. MTT's already explored human
triplets and FMA VALIDATION cannot become independent holdouts
retroactively.

## Local data protection and Lyrion operation

- Keep song names, source URLs, audio hashes, individual reviews,
  and per-track vectors **on the user's local machine**.
  Commit only synthetic tests and scripts; upload aggregated,
  non-identifying results solely when explicitly authorized.
- The existing
  [`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
  may queue deliberately selected pairs. Before any actual queue
  mutation, repeat the dry run, player ID/track ID resolution,
  and duplicate-preservation checks. This planning document
  does not authorize automatic playlist changes.
- The first pilot exposed a semicolon-delimited CSV import issue.
  Define CSV delimiters explicitly or use the existing
  evaluator's comma-separated format.
- Build/test research code in GitHub Actions; no unplanned
  local Windows Rust build.

**Status:** Steps L0–L3 are documented but deliberately
**not yet executed**. The local read-only preflight is
the next independent activity if DEAM remains source-blocked.
