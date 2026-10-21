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

**Build verified:** [Windows x64 research run 39661674510](https://github.com/chrober/bliss-mood-poc/actions/runs/39661674510) PASSED, including the pinned Rust-v5 source check, song-embedding unit tests, executable startup and `--embedding-out` CLI option. The [`research-song-embedding-windows-x64` artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39661674510) contains only the experimental executable, available runtime DLLs, `BUILD.txt`, and `SHA256SUMS.txt`; it includes **no original audio, models or per-track features**. This does not certify complete real-song Windows/C++ parity.

**Local export helper:** [`scripts/export_local_song_embeddings.py`](../scripts/export_local_song_embeddings.py) uses the original compatible schema-v3 research head cohort and is **dry-run by default**. It validates the experimental binary and executable SHA, the local encoder and classifier ONNX SHA against the stored head metadata, FFmpeg/ffprobe availability and **each original audio SHA** before allowing any output. Its track selection is bounded to at most 100 songs. There are **no private track names, paths, or vectors in stdout**.

Only explicit `--execute` enables inference, using `analyze-features --embedding-out` **without `--db`**. Outputs go to a **new local, Git-ignored `benchmark-*/` directory**, named by SHA256 of exact song keys. Existing JSON is never overwritten; an interrupted output directory can be used again only with explicit `--execute --resume`, after revalidating existing JSON. Existing head SQLite data stays read-only. The official model weights and FFmpeg/ffprobe must already exist on the user's machine.

**First user action:** retrieve the [verified Windows artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39661674510) into an ignored `bin/` subdirectory, then perform only a **one-song preflight** on the existing local DB, with the correct local audio root. The PowerShell handoff can run `gh run download 39661674510 --repo chrober/bliss-mood-poc --name research-song-embedding-windows-x64 --dir <ignored-bin-folder>`; after that, run the helper with `--db`, `--audio-root`, `--models-dir`, `--binary`, `--out-dir`, `--limit 1`, and `--seed 20261021`, **without `--execute`**. A successful dry-run outputs `status=dry_run_verified_no_changes`, `sample_count=1`, `audio_sha_verified=1` and `model_files_sha_verified=3`. Verify this before exporting even one song. No music/audio files or local SQLite/embeddings are uploaded.

**Previous verified library baseline:** 100/100 correctly dimensioned and compatible 87D/56D v5 feature pairs, zero head provenance mismatches. Direct 1280D availability was **not assessed** (no embedding directory), so the initial report did not establish that those sidecars were absent.

**Research test gates:** [synthetic Linux and Windows tests 39662462594](https://github.com/chrober/bliss-mood-poc/actions/runs/39662462594) PASSED for dry-run/no-change, model and audio drift, unsafe track keys, missing/existing exports, validation, resume and no-overwrite. The next independent human review remains phase 3 and does not require a whole-library rescan.
