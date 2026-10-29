# WP3-R3 real-data adapter and WP2-P3 pinned learner execution (2026-10-29)

> **New concrete source bridge / 29 October 2026:** Real artist and album group provenance no longer needs to be manually fabricated if [existing BlissMixerLab artist-repeat-identity snapshot and Lyrion SQLite library metadata](bliss-essentia-lyrion-existing-metadata-source-20261029.md) are accessible on the same research host. [derive_lyrion_research_groups.py](../scripts/derive_lyrion_research_groups.py) creates the strictly private group JSON from 4 validated read-only sources, and the [one-block Windows launcher](../scripts/run_grouped_bliss_essentia_research_windows.ps1) runs it together with the local teacher study on a controlled seed/limit. Research CI passes Linux/Windows; the adapter has **not** been tested with actual private library databases. The user must not be asked to manually enter or upload artist group labels, and must not be asked to rescan music or repeat the completed 12 ratings.


**Status: code and synthetic verification, not a private-library execution.**
Work is isolated on `feat/general-pairwise-similarity-research`; Draft PR #16,
`main`, `bliss-learner` and `lms-blissmixer-lab` remain unchanged.
The [unified three-workstream architecture](similarity-three-workstreams-strategy-20261029.md)
is still binding: WP1 General remains available without training, WP2 personal
learning is optional but active, and WP3 prioritizes studying and potentially
improving **Bliss 23D itself**, not simply appending an Essentia score.

## WP3-R3: aggregate-only real joined-data adapter

Implementation: [run_local_bliss_essentia_teacher_study.py](../scripts/run_local_bliss_essentia_teacher_study.py).

This is the first integrated **local real-source adapter** for the existing
R0/R1/R2 research protocols. Inputs are:

1. An **existing** Bliss `bliss.db` with exact `TracksV2.File` and all
   23 original bliss-learner columns.
2. An **existing** experimental Essentia schema-v3 `feature_tracks` and
   `feature_models` SQLite sidecar with coherent Genre 87D and Mood 56D
   heads and compatible source SHA/model provenance.
3. A separate **explicitly permissioned PRIVATE JSON mapping** from
   exactly matching `TracksV2.File` keys to
   `artist_group`, `album_group`, `recording_group`:

```json
{
  "opaque/original/track-file-key-1": {
    "artist_group": "opaque_artist_group_A",
    "album_group": "opaque_album_group_B",
    "recording_group": "opaque_recording_group_C"
  }
}
```

These must refer to **real, trustworthy group identities**, not fabricated
name/path prefixes. There is no fallback to a guessed artist from a filename,
a basename match, fuzzy identity or a row ID; any sampled otherwise eligible
song lacking grouping evidence causes the requested study to **fail closed**.
No new music analysis is performed, and the audio bytes are never read or
downloaded.

Using deterministic reservoir sampling of the existing paired head cohort
(`--seed`, `--limit`, default at most 400, maximum 4,000),
the runner validates head provenance, reads Bliss in SQLite `mode=ro`
with `query_only=ON`, and constructs only an **in-memory** paired
dataset. It reuses the preexisting grouped partition and then runs:

- The train-selected, group-holdout verified Bliss–Genre and Bliss–Mood
  Pearson/Spearman descriptive correlations.
- Training-only `StandardScaler`/Ridge, PLS and PCA-limited CCA to
  predict or describe Essentia **teacher outputs**.
- A **Bliss-only 23D inference** student geometry fitted by training
  with Genre/Mood teacher scores, compared on heldout groups against
  original and train-standardized Bliss and a permutation negative
  control.

A successful run writes only a **new aggregate JSON** supplied through
`--out`; it refuses any existing target. The output does not contain
individual song keys, album/group names, paths, per-song vectors, model
weights or direct audio hashes. The seed, dimensions, coverage counts,
estimated associations, teacher-prediction errors, distance-rank
agreement and explicit limitations are retained. Failures print only
generic input-compatibility errors, not private content. Source databases
and group metadata are unchanged. No result is uploaded by this script.

**Important limitations:** matching historical file keys does *not*
prove byte-identical Bliss/Essentia source audio; publisher/model
training overlap is **not** certified absent; Essentia's genre/mood
outputs remain noisy **pseudo-teachers**. Even a successful grouped
teacher-distance reconstruction does **NOT** establish better human
music similarity or playlist transitions. This is exploratory
development, and the previous MTT/FMA/DEAM holdout restrictions
remain in force. Group splits are conditional on accurate external
metadata; this code cannot independently certify that metadata.

The [synthetic integration tests](../tests/test_run_local_bliss_essentia_teacher_study.py)
create two *real schema-shaped but artificially populated*
SQLite sources and explicit groups. They verify exact-key joins,
complete source protection and non-identifying report outputs,
repeatability, strict missing-group failure and non-overwrite.
They run on both Linux and Windows with the pinned scikit-learn
environment from
[requirements-wp3-r2.txt](../research/requirements-wp3-r2.txt).
**No real user library, personal audio or private survey was accessed
for this work.**

### Real-data run prerequisites (not executed)

Before a first real run, an operator must provide actual **explicit,
approved** read-only paths to the above three inputs, confirm the model
and feature versions, license rights and genuine grouping provenance
and ensure a sufficient connected-component group holdout. A local
Windows launcher must make its own source and SHA checks, update an
**isolated clean worktree** and verify Python/scikit-learn rather
than making undocumented assumptions about a machine, learner path,
LMS server, dataset or release binary. A trustworthy
`group-metadata-json` cannot be manufactured from filenames.
Do not run on an arbitrary unverified personal music library solely
to fill an empty report.

## WP2-P3: existing Rust learner invocation is now separately verifiable

Implementation: [run_verified_bliss_learner.py](../scripts/run_verified_bliss_learner.py).

It consumes a bundle previously prepared by
[prepare_bliss_learner_train_only.py](../scripts/prepare_bliss_learner_train_only.py).
The caller must provide **the exact existing learner executable**,
an independently trusted 64-digit SHA256 pin, a new private output
directory and an optional bounded timeout.

The script requires that the original private staging manifest,
staged SQLite and train-only triplet JSON exist and hash-match; it
rechecks all triplet identities and requires that the **entire
staged TracksV2 song set equals the training-triplet song universe**
(with no hidden extra songs), all with valid 23D values. A forged
manifest cannot simply rename the full production DB as a training
source. It refuses any existing result directory or suspicious
source symlink, then invokes the existing Rust binary directly
with the staged `--db`, staged `--triplets` and a **new** `--output`
path. It does **not** request `--notifs`, LMS callbacks or network.
Subprocess logs are suppressed to avoid accidental private song
identity disclosure. Inputs and executable hashes are verified
again after the learner returns.

The resulting 23×23 matrix is checked for finite numeric values,
correct legacy JSON dimensions, symmetry and approximate PSD
sanity. An additional **private** run manifest records input
hashes, executable hash, output matrix hash, train vote count,
and the known limitations. The public/console return is only
nonidentifying counts and status flags.

The learner remains **unmodified** and its internal random lambda
cross-validation does not become artist/album grouped by this
operation. Its final matrix is trained on the **supplied staged
TRAIN ONLY** triplets, not the external holdout; however an
executable pin is a content-integrity check, **not** a proof of
its source revision, security, algorithm selection or an
independent musical performance improvement. No output
may be activated as Personal merely because the matrix is
well formed. It must still pass the independent personal
holdout, calibration, model compatibility and 0–100% General/
Personal fallback requirements.

[Mock-only integration tests](../tests/test_run_verified_bliss_learner.py)
verify correct binary argument restrictions, checksums,
complete training-song universe, tamper detection, numerical
matrix validation and output non-overwrite. They **never run**
an external binary or use a real person's preferences.

## Next research gates

- **WP3**: find or provide a permissioned, *genuinely grouped*
  same-song Bliss/Essentia paired data source. Only then run
  exploratory real correlations and teacher reconstruction;
  separately select and test transformed Bliss against an
  independent **musical similarity reference**. Evaluate
  source diversity, label imbalance, data overlap and artist/
  album leak.
- **WP2**: a trained private matrix requires an authorized
  real triplet dataset, verified binary hash and a genuine
  holdout. Run only on the isolated training bundle and
  evaluate blind holdout preferences separately; never
  request further *mandatory* user listening.
- **WP1**: continue the reliable General Metric research
  in parallel. A failed prior MTT archive transfer was
  not evidence of a worse metric.
- **Safety**: do not rerun the completed native 100-song
  comparison, touch PR #16, alter original databases,
  rerun worker tuning or optimize for one host/library.
