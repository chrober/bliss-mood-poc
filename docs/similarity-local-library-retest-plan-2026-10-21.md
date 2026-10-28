# Lyrion — next local song-representation listening comparison

## Human review complete; evaluator available (2026-10-28)

The 12-pair listening exercise has **already been completed**:
12 evaluated pairs, 24 distinct tracks, 60 valid numeric
human ratings and seven comments. Excel exported the
reviewed CSV as **tab-delimited CP1252/Windows-1252**;
do not load it as comma-delimited UTF-8 by default.
Pair **10** includes spoken interview/comment rather
than ordinary music, according to the human reviewer.
Treat it as an explicit data-quality sensitivity case,
not as a wrong vote.

The separate [ordinal pilot evaluator](../scripts/evaluate_local_listening_pilot.py)
now supports this Excel CSV and the frozen local
`selection-audit-private.json`. It performs strict
12-pair identity/order matching before comparing
five untrained score methods with four human rating
dimensions. Pair 10 is kept in the all-pairs report
and flagged for a separate eleven-music-pair comparison.
Only numbered and aggregate data are written
to a new, private ignored output directory.

**Do not regenerate or overwrite the hearing CSV,
re-run embedding inference, or open a new music queue
for this same pilot.** The next action is to execute
the [private local 12-pair evaluation runbook](similarity-local-listening-pilot12-evaluation-2026-10-28.md),
which contains a complete `& { ... }` Windows PowerShell
block with `--nonmusic-pairs 10` and a safe output-folder
existence check. The model-score audit is not included
in the user's chat attachment, so the true model-vs-human
correlations **remain uncomputed until this local
command runs**. Keep the original CSV, audit, audio
and song identifiers off GitHub.

## Current status and new optional-personalization design (2026-10-22)

**This file also preserves old execution notes for reproducibility.**
The user has **already completed** the corrected local one-song
research export, the 100-song embedding export and the independent
final audit: **100/100 same-song matching Genre 87D, Mood 56D,
and Audio 1280D features, zero missing or incompatible embeddings**.
The **12-pair blinded M2 review instrument has already been
generated locally**, using 24 distinct tracks with all human
rating fields originally empty (now completed as documented above). **Do not rerun historic one-song/100-song
export examples as the current next step**; the private
model-score selection audit remained sealed until the reviews
were completed; it may now be used in the local evaluator.

The research direction is extended, not replaced: independently
evaluate the strongest **general-purpose** metric without any
per-user training; add only **optional** per-listener triplet
learning and a **0–100% personal influence** blend after
calibration. With no usable learned model, effective scoring
is **100% general**, regardless of slider position.
The current blinded 12-pair study remains primarily
**general-metric evidence**; designing a personalized
triplet learner is a separate parallel experiment.
See the binding
[general/personal architecture decision](similarity-general-personal-blending-architecture.md)
and [current chat handover](chat-handover.md).

## Critical Windows research CLI correction (2026-10-21)

**The original binary from [run 39661674510](https://github.com/chrober/bliss-mood-poc/actions/runs/39661674510) is obsolete. DO NOT use it.**
It accidentally retained Rust-v5's original `--db`/`--track-key` pairing restriction,
so `analyze-features --track-key <key> --embedding-out <new-json>` without
`--db` failed *before inference*. The user's local one-song attempt therefore
reported `incomplete_do_not_use_for_scoring`, `failed=1`. Source audio,
official models and exact fingerprints had already passed their preflight
checks; the head SQLite database was unchanged.

**Fixed:** [research-only overlay commit `a7e270d`](https://github.com/chrober/bliss-mood-poc/commit/a7e270d2878e7fd20fcb35d3d9d0fa9324418e2d).
The patched CLI permits `--track-key` without `--db` **only if
`--embedding-out` is also present**. Head persistence and other
command rules are otherwise unchanged.

**Replacement Windows artifact:** [run 39664316069](https://github.com/chrober/bliss-mood-poc/actions/runs/39664316069)
**PASS**, artifact `research-song-embedding-windows-x64`.
The actual synthetic-audio ONNX regression with
`--track-key + --embedding-out` and no SQLite DB
[passed in Linux run 39664440263](https://github.com/chrober/bliss-mood-poc/actions/runs/39664440263),
including a bit-for-bit match of the new and existing song
embedding vectors. The local exporter now **requires the exact
fixed overlay commit** in the binary's `BUILD.txt` and reports
only aggregate failure stage counts:
`cli_nonzero_exit`, `embedding_file_not_created`,
`embedding_validation_failed`, and `existing_embedding_invalid`.
Do not print or upload Rust stderr with private song paths.

**Retry only one song, not 100:** Download the replacement artifact
into a **new** ignored `bin/` directory and use an unused
`benchmark-*/` output directory; leave the failed folder untouched.
Run the bounded exporter with `--limit 1 --seed 20261021 --execute`.
The exporter independently revalidates audio/model/binary hashes
and never passes `--db` to the research binary.
Proceed to the remaining songs only if this complete real
Windows one-song run verifies successfully.

**Historical status (October 21, 2026):** Originally a planning document; **superseded by the successful 100-song export and completed pilot generation above**.
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

## M1 / L0 implementation: auditable feature readiness, not a library scan

The first narrow implementation is now
[`scripts/audit_local_feature_readiness.py`](../scripts/audit_local_feature_readiness.py)
with synthetic
[`tests/test_audit_local_feature_readiness.py`](../tests/test_audit_local_feature_readiness.py).
It uses **only standard Python modules**, opens an existing schema-v3
SQLite sidecar with `mode=ro` and `PRAGMA query_only=ON`, and
does not invoke the Rust scanner, ONNX, LMS or an audio decoder.
It emits aggregate JSON and **never reports private track keys, audio hashes,
per-song vectors or individual listening labels**.

On an existing eligible head cohort it deterministically selects at most
100 same-song pairs (configurable 1–300), and checks:

- Both dominant model cohorts use corrected
  `experimental-essentia-audio-v5-f32-src-ratio-unvalidated` frontend
  and the expected 87D / 56D classifier dimensions, nonconstant
  finite scores, ordered unique class identifiers and correct
  aggregation.
- Each sampled song has compatible exact track keys, nonzero
  patch counts, equal head audio SHA256, the same encoder name/SHA,
  and valid model-source hashes in both classifier records.
- If a **local private** `--embedding-dir` is supplied,
  it checks the versioned 1280D export, song-key-derived file name,
  song key/audio SHA, encoder SHA, patch count, pooling/fingerprint,
  preprocessing and unit L2 norm. Missing and invalid sidecars
  are counted **separately**. Without the directory, coverage is
  **not assessed**, never falsely counted as zero.
- Previous SQLite bytes remain unmodified; an optional output JSON
  path is created only when new, refusing overwrite.

**Scope:** This audits declared provenance and internal consistency,
not independent C++ numerical parity or model correctness. A positive
report does **not** complete phase 0 or authorize product use.
The report records the full compatible-pair count **before sampling**,
the number of malformed paired vectors excluded, and the counts on
the selected bounded sample. An absent embedding directory is
not evidence that no 1280D vectors exist elsewhere.

### First local execution (Windows PowerShell, no queue or audio changes)

After updating the local clone to the PR #16 branch, use the already
available corrected Rust-v5 feature-sidecar DB. The path below reflects
the previous research pilot; verify that it exists locally rather than
assuming it is still current.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    $Db = Join-Path $Repo 'benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db'
    $Audit = Join-Path $Repo 'scripts\audit_local_feature_readiness.py'

    if (!(Test-Path -LiteralPath $Repo -PathType Container)) {
        throw 'Set $Repo to the existing local repository clone.'
    }
    if (!(Test-Path -LiteralPath $Audit -PathType Leaf)) {
        throw 'Audit script not found. Update your local PR #16 branch first.'
    }
    if (!(Test-Path -LiteralPath $Db -PathType Leaf)) {
        throw 'Research sidecar not found. Set $Db to the previously analyzed local schema-v3 file.'
    }

    Push-Location -LiteralPath $Repo
    try {
        & python $Audit --db $Db --limit 100 --seed 20261021
        if ($LASTEXITCODE -ne 0) {
            throw "Read-only feature audit failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
```

**Expected output:** `lyrion-local-feature-readiness-aggregate-v1`
JSON printed to the local console, including numbers of compatible
Genre/Mood song pairs, provenance mismatches, and
`embedding_status=not_assessed_no_directory` unless a private
embedding folder is deliberately supplied. No user song
identifiers appear in that JSON, making it suitable for discussing
the aggregate counts. **Do not upload the local SQLite database,
raw music, individual embeddings or listening CSV.**

**Next decision, not yet executed:** Use the measured
head coverage and any known local embedding-sidecar location
to decide whether bounded additional 1280D exports are necessary.
Do not scan the whole library or propose listening pairs until
this inventory is reviewed. This is **M1 only**, not the M2 listening pilot.

## M1 checkpoint: Windows experimental research binary and bounded local exporter

**Build verified:** [Windows x64 research run 39664316069](https://github.com/chrober/bliss-mood-poc/actions/runs/39664316069) PASSED, including the pinned Rust-v5 source check, song-embedding unit tests, executable startup and `--embedding-out` CLI option. The [`research-song-embedding-windows-x64` artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39664316069) contains only the experimental executable, available runtime DLLs, `BUILD.txt`, and `SHA256SUMS.txt`; it includes **no original audio, models or per-track features**. This does not certify complete real-song Windows/C++ parity.

**Local export helper:** [`scripts/export_local_song_embeddings.py`](../scripts/export_local_song_embeddings.py) uses the original compatible schema-v3 research head cohort and is **dry-run by default**. It validates the experimental binary and executable SHA, the local encoder and classifier ONNX SHA against the stored head metadata, FFmpeg/ffprobe availability and **each original audio SHA** before allowing any output. Its track selection is bounded to at most 100 songs. There are **no private track names, paths, or vectors in stdout**.

Only explicit `--execute` enables inference, using `analyze-features --embedding-out` **without `--db`**. Outputs go to a **new local, Git-ignored `benchmark-*/` directory**, named by SHA256 of exact song keys. Existing JSON is never overwritten; an interrupted output directory can be used again only with explicit `--execute --resume`, after revalidating existing JSON. Existing head SQLite data stays read-only. The official model weights and FFmpeg/ffprobe must already exist on the user's machine.

**First user action:** retrieve the [verified Windows artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39664316069) into an ignored `bin/` subdirectory, then perform only a **one-song preflight** on the existing local DB, with the correct local audio root. The PowerShell handoff can run `gh run download 39664316069 --repo chrober/bliss-mood-poc --name research-song-embedding-windows-x64 --dir <ignored-bin-folder>`; after that, run the helper with `--db`, `--audio-root`, `--models-dir`, `--binary`, `--out-dir`, `--limit 1`, and `--seed 20261021`, **without `--execute`**. A successful dry-run outputs `status=dry_run_verified_no_changes`, `sample_count=1`, `audio_sha_verified=1` and `model_files_sha_verified=3`. Verify this before exporting even one song. No music/audio files or local SQLite/embeddings are uploaded.

**Previous verified library baseline:** 100/100 correctly dimensioned and compatible 87D/56D v5 feature pairs, zero head provenance mismatches. Direct 1280D availability was **not assessed** (no embedding directory), so the initial report did not establish that those sidecars were absent.

**Research test gates:** [synthetic Linux and Windows tests 39662462594](https://github.com/chrober/bliss-mood-poc/actions/runs/39662462594) PASSED for dry-run/no-change, model and audio drift, unsafe track keys, missing/existing exports, validation, resume and no-overwrite. The next independent human review remains phase 3 and does not require a whole-library rescan.

## M1 COMPLETE; start M2 blinded 12-pair same-song pilot (2026-10-21)

**User-measured final L0 result:** The user's existing 100-track
schema-v3 feature DB has **100/100 compatible 87D Genre and 56D
Mood/Theme vectors**, with zero joined invalid vectors and zero
provenance mismatches. The corrected Windows research CLI successfully
exported **100/100** new 1280D sidecars, with zero CLI, missing-file
or validation failures. The follow-up independent
[`audit_local_feature_readiness.py`](../scripts/audit_local_feature_readiness.py)
over the same DB and new embedding directory reported
`embedding_valid=100`, `embedding_missing=0`,
`embedding_invalid_or_incompatible=0`, and
`compatible_head_pairs=100`. The existing database is unchanged.
**This closes only the bounded phase-2 research-cohort feature-coverage
gate**; phase-0 release/C++ numerical gates remain open.

**No additional ONNX/audio analysis is needed for the pilot.** Use
[`scripts/propose_local_embedding_ab_pilot.py`](../scripts/propose_local_embedding_ab_pilot.py)
to produce a **new**, local, model-blind 12-pair human-review CSV.
It fails closed unless it can independently revalidate **all 100**
exact matching recording hashes, encoder and pooling fingerprints,
classifier model cohorts and 1280D sidecars. It scores the 4,950
possible unique song pairs using
Genre Cosine, Genre Centered Cosine, Mood Cosine,
Mood Centered Cosine and Audio-Embedding Cosine. It uses within-cohort
ranks **only to select contrasts**, not as genre, mood or human labels.

The fixed **exploratory pilot sampling quotas** are three high-Genre,
two high-Mood, two high-Embedding, two Genre-over-Embedding
disagreements, two Embedding-over-Genre disagreements, and one
low-all control. It uses 24 distinct song keys (no song repeats),
prefers cross-artist pairings based only on a weak path-derived hint,
shuffles pair presentation reproducibly, and can exclude previously
reviewed pairs via `--exclude-reviewed` (CSV with `left,right`).
**A model-high-Genre candidate is not a human Genre-positive
control**. Do not interpret these purposively selected pairs
as a random sample, holdout test, or validated musical neighbors.

The new `listening-pairs.csv` has only exact `left` and
`right` track keys and blank review columns:
`genre_similarity_1to5`, `mood_energy_similarity_1to5`,
`timbre_similarity_1to5`,
`next_track_suitability_1to5`, `confidence_1to3`,
and `notes`. Suggested scale for each quality dimension:
**1 = very different/unsuitable; 3 = mixed or moderate;
5 = very similar/suitable**. Leave a field blank if unable to
assess. Confidence 1 = low, 2 = moderate, 3 = high.
The playlist-transition rating refers to **left then right**.
All rating cells must be entered by a human, not generated from
model similarity.

The separate `selection-audit-private.json` includes the
sampling strata and model scores keyed by track identities.
**Do not inspect it before finishing ratings, upload it, or
commit it.** Unlike the earlier binary `genre_label`/
`mood_label` CSV, the new ordinal 1-to-5 pilot CSV is **NOT**
accepted by the old binary-label similarity evaluator; scoring
must be implemented separately after collecting the human responses.

### Complete local PowerShell generation (no player or playlist changes)

Run this in the existing local PR #16 research clone.
The named output folder must not already exist. The optional
`LYRION_PREVIOUS_LISTENING_CSV` environment variable may contain
a previous review CSV to exclude already-rated song pairs; if
not present, no earlier-pair exclusion is claimed.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    $Branch = 'feat/similarity-metric-evaluation'
    $Db = Join-Path $Repo 'benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db'
    $Embeddings = Join-Path $Repo 'benchmark-local-song-embeddings-full100-20261021'
    $Script = Join-Path $Repo 'scripts\propose_local_embedding_ab_pilot.py'
    $Out = Join-Path $Repo 'benchmark-local-blinded-ab-pilot12-20261021'
    $EarlierReview = [string]$env:LYRION_PREVIOUS_LISTENING_CSV

    if (!(Test-Path -LiteralPath $Repo -PathType Container)) {
        throw 'Local repository clone not found.'
    }
    Push-Location -LiteralPath $Repo
    try {
        $Current = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0 -or $Current -cne $Branch) {
            throw "Expected research branch: $Branch"
        }
        & git pull --ff-only origin $Branch
        if ($LASTEXITCODE -ne 0) { throw 'Git pull failed.' }
        foreach ($InputPath in @($Db, $Embeddings, $Script)) {
            if (!(Test-Path -LiteralPath $InputPath)) {
                throw "Required local research input missing: $InputPath"
            }
        }
        if (Test-Path -LiteralPath $Out) {
            throw 'Review output directory already exists. Human ratings must never be overwritten.'
        }
        $ArgsList = @(
            $Script, '--db', $Db,
            '--embedding-dir', $Embeddings,
            '--out-dir', $Out
        )
        if (-not [string]::IsNullOrWhiteSpace($EarlierReview)) {
            if (!(Test-Path -LiteralPath $EarlierReview -PathType Leaf)) {
                throw 'Configured previous listening CSV does not exist.'
            }
            $ArgsList += @('--exclude-reviewed', $EarlierReview)
        }
        & python @ArgsList
        if ($LASTEXITCODE -ne 0) {
            throw 'Blinded pilot selection failed. No audio or Lyrion changes were made.'
        }
    }
    finally {
        Pop-Location
    }
}
```

Expected **aggregate** output:
`status=BLINDED_REVIEW_READY`,
`source_song_count=100`, `pilot_pairs=12`,
`unique_songs_in_pilot=24`,
`all_human_rating_cells_blank=true`.
These numbers describe a generated local instrument,
**not measured human judgments**.
Send only that aggregate summary for review before any player
queue mutations. The existing
[`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
reads the `left,right` CSV columns, but it must be
configured and run with `LYRION_APPLY=false` first,
independently of this research-only selector.
Preserve all original eight human ratings and keep the new
human review files local.
