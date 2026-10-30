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


## Real Windows source run: successful, 30 October 2026

The operator ran the full Python 3.15 launcher and provided only
anonymized console output. The private research SQLite was generated
at an ignored local path under benchmark-wp3-research-20261030-064618-7f8c43a3.
The existing same-100 source yielded:

- Eligible Genre/Mood head pairs: **100**.
- Native feature vectors excluded: **0**.
- Provenance rejections: **0**.
- Missing, ambiguous or invalid Bliss23: **0**.
- Exact-key paired Bliss23 + Genre87 + MoodTheme56: **100**.
- Four original source roles have NOT all been provided: the optional
  BlissMixerLab snapshot and Lyrion library SQLite are not configured.
- Group status: **NOT_AVAILABLE**, blocker
  LYRION_GROUP_SOURCES_NOT_PROVIDED; group-heldout train and teacher
  metric learning must remain disabled.
- Source databases reported unchanged. No music-quality winner or
  cross-source audio-byte identity certification was claimed.

This is a real user-executed local data-build result, **not** a
GitHub-hosted re-creation of personal library features. Original private
feature data must remain on that Windows computer; only aggregate counts
may be shared.

## WP3 next activity: descriptive correlations without group leakage

Because the 100 Bliss23/Essentia87+56 vectors are already paired, an
additional **descriptive-only** analysis may proceed while artist/album/
recording metadata is missing. This does not learn a metric, choose
fusion weights, reconstruct Essentia teacher outputs, or claim
independent heldout predictive quality.

New files:

- [Python stdlib descriptive script](../scripts/analyze_wp3_snapshot_correlations.py)
- [Complete one-block PowerShell 5.1/7 entrypoint](../scripts/analyze_wp3_snapshot_correlations_windows.ps1)
- [Synthetic unit tests](../tests/test_analyze_wp3_snapshot_correlations.py)

On the local research branch, after updating via git pull --ff-only,
run the PowerShell entrypoint. It finds the **one** existing private
benchmark-wp3-research-*/wp3-research.sqlite automatically. If more
than one research DB exists, it **fails closed** until the operator
selects a specific known input via LYRION_WP3_RESEARCH_DB. It NEVER
guesses a newest DB or requests the original four SQLite paths again.

The report computes ordinary Pearson and tie-aware Spearman across
all 23 Bliss dimensions times 87 genre/56 mood classifier dimensions,
**3289 candidate associations** (23×87 + 23×56). Constant/degenerated
feature pairs are excluded and counted rather than made zero.
It provides per-head numbers of defined pairs, median magnitude and
predefined effect-size thresholds, plus a bounded list of the
highest absolute Spearman associations, with their original Bliss
feature/Essentia class labels. No song keys, personal audio hashes,
song vectors, private DB file paths or listener evaluations are
printed or saved into the aggregate report.

Selection of the highest correlations from 3289 exploratory tests
creates a serious multiple-comparison and small-cohort winner's-curse
risk. Track independence, identity-group overlap, upstream training
overlap, and generalizability are not established. Therefore report
no confirmatory p-values and do not infer musical similarity gains.
The exact same 100 songs cannot serve as both model development
and independent human-labelled validation.

The analysis is stdlib-only on the existing **Python 3.15** and
opens the snapshot with mode=ro/query_only; original and private
snapshot DBs remain unchanged. The report is uniquely named
aggregate-wp3-descriptive-*.json in the same gitignored private run
directory and never overwrites a prior report. Do not commit or
upload the private snapshot itself.

## WP3 within-cohort redundancy/sensitivity follow-up — 30 October 2026

The user supplied an *anonymized* aggregate from 100 previously
analyzed native Essentia/Bliss songs (no private feature DB uploaded).
All exact 3,289 cross-feature correlations were defined with no
invalid vectors. The reported Spearman ρ extremes were:

- Genre: Chroma6 to metal +0.723552 and to hard +0.721092;
  Chroma12 to metal +0.715104; Chroma11 to easylistening −0.707459.
- MoodTheme: Chroma12 to soft −0.830495, Chroma11 to soft −0.805629,
  Chroma13 to soft −0.797144, Chroma12 to romantic −0.792559.

These are associations of model outputs on **one 100-song cohort**,
not evidence that the source Bliss chroma features cause or uniquely
predict mood, genre, or musical quality. Genre/mood model class
scores are neither independent artist labels nor ground truth.

**Implemented next executable (no new audio analysis, models, or metadata):**

- scripts/analyze_wp3_snapshot_stability.py (Python 3.15 stdlib);
- scripts/analyze_wp3_snapshot_stability_windows.ps1
  (standalone PowerShell launcher);
- tests/test_analyze_wp3_snapshot_stability.py (synthetic only).

The analysis opens the existing private wp3-research.sqlite in
read-only SQLite mode. It computes all 23*22/2 = 253 intra-Bliss
Spearman redundancy pairs, focused correlations among selected
Chroma components, classifier class redundancy across the original
Genre and MoodTheme heads, and 16 frozen feature/class pairs
selected from the **earlier SAME 100-SONG report**.

For each post-selected cross-feature pair, it reports original
Pearson/Spearman, maximum absolute Spearman difference after
leaving out any one song, and descriptive p10/median/p90 and sign
consistency from 200 seeded **80%-without-replacement** subsamples.
This is *within-original-cohort sensitivity*, NOT a statistical
confidence interval, true artist/album holdout, independent
replication or a learned similarity metric. Songs can be dependent
by artist/recording; selecting the original top 16 out of 3,289
creates winner's-curse and multiple-comparisons concerns.

After git pull --ff-only on the research branch, launch:

    & .\scripts\analyze_wp3_snapshot_stability_windows.ps1

If there is exactly one WP3 snapshot, it is selected. Otherwise set
LYRION_WP3_RESEARCH_DB to the explicit known existing SQLite path.
The script prints anonymized counts and writes a new uniquely named
aggregate-wp3-stability-*.json in the ignored private research
folder; it never exports song keys, hashes, individual vectors or
source DB paths. Each invocation refuses to overwrite old reports.

The next **genuinely independent evaluation** still requires
verified Lyrion artist/album/recording identities and a group-
disjoint holdout. BlissMixerLab/RepeatIdentitySnapshot.pm writes
under the dynamic LMS cache directory, not a verified accessible
Windows path. Do not manufacture artist metadata from filenames,
or mistake this report for WP3 teacher learning / WP1-WP2 gains.


## Metadata provenance source discovery

The existing plugin source
[BlissMixerLab/RepeatIdentitySnapshot.pm](https://github.com/chrober/lms-blissmixer-lab/blob/main/BlissMixerLab/RepeatIdentitySnapshot.pm)
creates artist-repeat-identities.sqlite under
Slim::Utils::OSDetect::dirsFor('cache') / BlissMixerLab, conditional
on the plugin's prepare() routine and a valid LMS last-scan/root
identity. This is a **dynamic Lyrion cache directory**, not
a verified Windows-accessible path. The LMS library SQLite
is another genuine external source. Do not guess a Raspberry Pi
mount, download a live SQLite without a consistent snapshot, or
substitute song-path-derived artist/album labels to bypass the
independent group holdout gate.


## Verification and constraints

Cross-platform CI runs synthetic SQLite integration tests. Windows CI
also creates fresh exact-path synthetic Bliss and native-feature fixtures,
executes the FULL launcher on Windows PowerShell 5.1 and PowerShell 7,
verifies each run created a separate private research DB, and tests
no-data interpreter runtime smoke. [Successful CI run](https://github.com/chrober/bliss-mood-poc/actions/runs/40951688893)
covered both operating systems and both Windows shells. These tests verify no-write
preflight, exclusive creation, source bytes unchanged, exact feature
dimensions, blocked metadata without invented groups, and eligible
grouped teacher calculations. CI synthetic pass **does not mean** the
user's actual input files have been read or their group quality passed.

Original audio, original Bliss/Essentia SQLite, main, PR #16, native
worker controls, original user listening labels and related repositories
remain unchanged. No new mandatory song ratings or rescans.
