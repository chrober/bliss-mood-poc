# WP3: consolidated private research SQLite (29 October 2026)

## Status and purpose

The preferred WP3 local workflow is to create **one new, private,
versioned research SQLite** from **already computed Bliss and
Essentia features**. A new audio scan is NOT required. The builder
and Windows entrypoint are:

- [Python builder](../scripts/build_wp3_research_db.py)
- [Full standalone Windows Python 3.15 script](../scripts/build_wp3_research_db_windows.ps1)
- [Synthetic integration tests](../tests/test_build_wp3_research_db.py)

The output is research schema v1 (identity:
lyrion-wp3-research-snapshot-v1), **not** the production scanner
schema-v3 sidecar. Do not deploy it to Lyrion as a mood.db replacement.

## Known, exact original inputs

The complete Windows launcher uses the exact previously documented
files relative to D:\LMS\bliss-mood-poc:

1. bliss.db: upstream Bliss TracksV2.File and 23 original feature columns
2. benchmark-native-similarity-100-20261029\native-features.sqlite:
   existing native original Essentia C++ same-100-song Genre87/Mood56
   classifier feature SQLite.

The second file is documented by the successful technical native-vs-Rust
comparison on branch feat/native-similarity-cohort-validation at
docs/native-similarity-100-real-results-20261029.md. Its reported
PASS_EXPLORATORY_TOLERANCES is backend continuity evidence, not a
validated general musical similarity score. Neither file path is
merely guessed from conventional filenames. If either source is missing,
the launcher stops without creating an output.

For an explicitly known *alternative existing* schema-v3 feature
SQLite, set environment variable LYRION_FEATURE_DB. No automatic
recursive folder searching or missing-song audio extraction occurs.

Optional, genuine Lyrion grouping sources can be supplied together as
LYRION_REPEAT_SNAPSHOT_DB and LYRION_LIBRARY_DB. No verified accessible
Windows path for either is recorded. This additional source must satisfy
the BlissMixerLab artist-repeat snapshot and actual Lyrion library
schemas, plus matching LMS track ID, URLMD5 and artist/album identifiers.
Never guess artist, album or recording from song filenames.
A matching historical snapshot's scan/root metadata **shape** is checked
but the freshness against live LMS is not independently certified.

## Database content and guarantees

The builder uses read-only SQLite connections and query_only mode,
then the exact binary Bliss TracksV2.File / feature_tracks.track_file
join, and rejects mismatched classifier preprocessing, model fingerprints,
bad vectors and inconsistent shared model/audio provenance.

The PRIVATE paired_tracks table holds exact track identifiers, Bliss23
f64, Genre87 f32, MoodTheme56 f32, audio SHA256, patch/encoder
identifiers and nullable artist/album/recording groups. The metadata
table stores sample seed/limit, model class order and provenance, group
readiness, and **private source paths and their original SHA256s**.
Source files are hashed before and after and never modified.

Only anonymized coverage counts and readiness codes go to stdout.
The SQLite output itself contains sensitive song keys/features/hashes;
NEVER publish or commit it. It is written to a unique ignored local
benchmark-wp3-research-*/wp3-research.sqlite destination, created
exclusively; existing private outputs are never overwritten.

The sample bound is 300, but the initial native source has at most
the 100 already analyzed songs. This is **not a full-library database**.
Even exact file-key overlap between Bliss and Essentia does not
independently prove identical audio bytes.

## One local entrypoint

From the local repo on feat/general-pairwise-similarity-research,
first update it using git pull --ff-only; then invoke this full
PowerShell file directly:

    & .\scripts\build_wp3_research_db_windows.ps1

The launcher always uses the existing Python 3.15 and never installs
a different Python version. It runs a read-only/no-write preflight first.
After a usable join, it writes only the new private research DB.

If optional identity sources are missing or blocked, group columns
remain NULL; the source feature snapshot remains useful for feature
availability and unsupervised research but **teacher learning and
grouped heldout evaluation are not started**. This is a truthful
blocking result, not a failed music analysis or a reason to invent
artist/album identity.

Only if genuine independent artist/album/recording groups pass do we
build an isolated Python 3.15 venv with the pinned research requirements
and invoke the existing train-only teacher/correlation models via the
new --research-db option. That entrypoint reads the research SQLite
and checks group readiness and seed; it no longer needs three original
DB paths or an external private group-JSON file.

Teacher reconstruction is NOT independent musical-similarity quality
validation. WP1 General Metric and WP2 optional Personal Metric
Learning are not replaced by this data-preparation step.

## Verification and constraints

Cross-platform CI runs synthetic SQLite integration tests and Windows
PowerShell 5.1/7 executable launcher smoke tests. They verify no-write
preflight, exclusive creation, source bytes unchanged, exact feature
dimensions, blocked metadata without invented groups, and eligible
grouped teacher calculations. CI synthetic pass **does not mean** the
user's actual input files have been read or their group quality passed.

Original audio, original Bliss/Essentia SQLite, main, PR #16, native
worker controls, original user listening labels and related repositories
remain unchanged. No new mandatory song ratings or rescans.
