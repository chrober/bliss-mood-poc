# WP3: consolidated private research SQLite (29 October 2026)

> **FOLLOW-UP RESEARCH INFRASTRUCTURE, NOT NEW MEASUREMENT (30 Oct 2026):** The confirmed real 100/100 grouped teacher study is the last measured WP3 result. The *next planned* new 240-song candidate cohort has not yet been executed. It uses a [frozen, unfitted MoodTheme Ridge hypothesis specification](../research/wp3-moodtheme-student-candidate-v1.json), [source-grounded independent-cohort selector](../scripts/prepare_wp3_independent_cohort.py) and [single Windows PowerShell entrypoint](../scripts/prepare_wp3_independent_cohort_windows.ps1), with strict exclusion of old 100 cohort's credited artist/album/recording identities, conservative MusicBrainz ID checks and seeded Bliss tempo/centroid quartile coverage. It does not run new audio/ONNX, evaluate human similarity, claim external validity or expose private song-level data. The selection manifest is new, ignored, private and must never be uploaded. [Protocol, tests and staged validation gates](wp3-independent-cohort-validation-plan-20261030.md).


> **LATEST VERIFIED REAL RESEARCH RESULT — 30 October 2026:** The operator has completed a 100-song, **75 train / 25 artist+album+recording-group-disjoint holdout** WP3 exploratory teacher-study using genuine Lyrion/BlissMixerLab metadata (88 connected groups). All 100 song identities matched authentic LMS IDs/URLMD5, with only one conservatively grouped unknown recording MBID. A new private `benchmark-wp3-research-20261030-091600-8c93d55f/wp3-research.sqlite` and an aggregate-only `aggregate-teacher-research.json` were generated without rescanning audio. On the 25-song holdout: best teacher-output MAE reduction vs train-mean baseline was **6.92% Genre87 (PLS)** and **13.04% MoodTheme56 (Ridge)**. Bliss-only MoodTheme Ridge student's Spearman correlation to Essentia teacher distances improved **0.442049 -> 0.540662** vs original Bliss Euclidean; Genre improved **0.557959 -> 0.569599**. These are **teacher-score/distance reconstruction** signals, NOT verified human-rated musical similarity. The 100 songs had been previously studied (3,289 correlations), so the group holdout is **not untouched confirmatory evidence**. Head parity validation, cross-DB audio-byte identity and teacher pretraining overlap remain unresolved. [Complete detailed experiment and next independent evidence gates](wp3-real-grouped-teacher-study-results-20261030.md).


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

Authentic Lyrion grouping sources are supplied together as
LYRION_REPEAT_SNAPSHOT_DB and LYRION_LIBRARY_DB. The operator has now verified
and privately copied the genuine Pi library and BlissMixerLab snapshot to
Windows (30 October 2026); see the [successful experiment](wp3-real-grouped-teacher-study-results-20261030.md). This additional source must satisfy
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

## Historical WP3 next activity (completed): descriptive correlations without group leakage

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

The next **genuinely confirmatory evaluation** still requires
a NEW independent cohort and a group-disjoint perceptual/human reference;
Lyrion artist/album/recording identities for the initial 100 songs are
now verified, but those 100 were already explored before the split. BlissMixerLab/RepeatIdentitySnapshot.pm writes
under the dynamic LMS cache directory, not a verified accessible
Windows path. Do not manufacture artist metadata from filenames,
or mistake this report for WP3 teacher learning / WP1-WP2 gains.



## Actual 100-song redundancy and sensitivity results, 30 October 2026

The user successfully ran the new private 100-song robustness analyzer
on the same Windows WP3 research snapshot and supplied the aggregate
report only. Schema: wp3-bliss-essentia-within-cohort-stability-v1;
status POST_SELECTED_WITHIN_COHORT_SENSITIVITY_NOT_EXTERNAL_VALIDATION.
No artists, raw song features, private file paths or model hashes were
uploaded. The report uses 200 deterministic 80-song samples (from the
same original 100), and exhaustive leave-one-track-out influence for
the 16 already selected feature/class relationships.

Observed within-cohort results:

- Every one of the 253 possible Bliss23-vs-Bliss23 Spearman pairs
  was defined. 22 had absolute rho at least 0.7; seven at least 0.9.
- Bliss Zcr vs MeanSpectralRolloff: +0.969277;
  MeanSpectralCentroid vs MeanSpectralRolloff: +0.968425;
  MeanSpectralCentroid vs MeanSpectralFlatness: +0.951683.
- Bliss Chroma11 vs Chroma12: +0.968089;
  Chroma12 vs Chroma13: +0.957912;
  Chroma6 vs Chroma12: +0.889901.
- Genre metal vs hard: +0.832871.
  MoodTheme soft vs romantic: +0.928557;
  soft vs nature: +0.894317;
  romantic vs nature: +0.883300.
  Cross-head genre metal vs moodtheme soft: -0.701494.
- All 16 post-selected associations retained their original sign
  in 200/200 80-song subsamples. The largest absolute change to
  Spearman rho when omitting exactly one of the 100 songs was
  0.024519 (MeanSpectralFlatness vs genre hard).
- Selected Chroma12 vs moodtheme soft: full rho -0.830495;
  within-cohort 80-song subsample p10/p90 [-0.848720,-0.809526].
  Chroma6 vs genre metal: full rho +0.723552;
  subsample p10/p90 [+0.687311,+0.752295].

Interpretation:

(1) The individual correlations are stable against single-record
deletion and selected random subsamples **within this cohort**.
(2) The Bliss chroma-derived descriptors and spectral brightness/noise
descriptors are strongly mutually redundant in this sample.
(3) Multiple Essentia head labels are also mutually redundant; one
candidate explanation is a broad hard/intense-versus-soft/romantic
model-score contrast, rather than 16 independent musical properties.
This is a hypothesis, not a scientifically established latent factor.
(4) Intra-cohort resampling cannot correct artist/album/recording
dependence, training-domain overlap, multiple-comparison selection
of 16 from 3,289, or the lack of independent human similarity
validation. p10/p90 are descriptive resampling percentiles, NOT
confidence intervals. The teacher output classes are not musical
ground truth or independent listener judgment.

**Research decision: do not fit or deploy data-derived feature weights
on the current 100-song cohort.** First obtain genuine Lyrion source
artist/album/recording group information, then study a larger
representation-diverse cohort with artist/recording-disjoint train and
holdout. Evaluate whether a Bliss-only candidate adds actual
independent **human-rated musical similarity** beyond original Bliss
and existing Genre/Mood/embedding baselines. A teacher-score
reconstruction result alone does not demonstrate that improvement.
Keep WP1 General Metric and WP2 optional Personal Metric Learning
as separate active workstreams and PR #16 isolated.

The plugin's identity snapshot path is dynamically derived from the
Lyrion cache root by BlissMixerLab/RepeatIdentitySnapshot.pm, then
BlissMixerLab/artist-repeat-identities.sqlite appended. Both sources were subsequently transferred as validated, private
Windows copies on 30 October 2026; see the real grouped-study record.
Do not fabricate identities from filenames. Before copying a live
SQLite from a running server, use a consistent snapshot/backup
procedure rather than risk an incomplete database; keep source
identifiers local, never in GitHub CI or reports.


## 30 October 2026: real Pi metadata discovery and PowerShell transfer repair

User authenticated to piCorePlayer (tc at 192.168.1.111), and read-only
diagnostics confirmed that /usr/local/slimserver/Cache resolves to
/mnt/mmcblk0p2/tce/slimserver/Cache. Source databases:

- /usr/local/slimserver/Cache/library.db (194.9 MB, 79,005
  tracks, 6,228 albums), last file write 30 October 2026 06:43.
- /usr/local/slimserver/Cache/BlissMixerLab/artist-repeat-identities.sqlite
  (59.2 MB, 77,517 track_identity rows, 76,870 artist identity
  rows), last file write 30 October 2026 07:32.

Read-only SQLite 3.32.1 schema inspection found the required
library tracks/album columns, snapshot identity/artist columns,
schema_identity lyrion-track-identities-v1,
lms_scan_time 1793339060 and a 64-character media root
fingerprint. Neither exact 100-song joins nor current scan
freshness are thereby independently established.

The first one-off Windows PowerShell copy script actually succeeded
at creating ONLINE SQLite backups on Pi and SCP transferring both
files, but FAILED at local Python validation before source-grouping
preflight: PowerShell native Python -c argument quote stripping
yielded SyntaxError on the SQLite URI expression. Its multiline
remote sh-s cleanup separately failed with unexpected EOF
(expecting fi), so the source copies might still exist in
/tmp/wp3-metadata-f15ad4f9c54340818830fcb14c08eeca. The
incomplete NEW Windows staging folder was then removed by the
caller. Original live SQLite files were not modified.

Permanent code repair:

- scripts/verify_wp3_copied_lyrion_sqlite.py is a standalone
  stdlib-only Python 3.15 CLI, using SQLite read-only quick_check,
  required columns and snapshot metadata shapes. No -c quoting.
- scripts/prepare_wp3_lyrion_group_sources_windows.ps1 reuses
  the already-successful remote read-only sqlite3 .backup/SCP
  sequence, creates an exclusive ignored local metadata folder,
  calls the Python CLI via explicit argument array, then uses the
  pre-existing derive_lyrion_research_groups.py --preflight with
  fixed seed 20261029, limit 100, read-only to verify LMS track IDs
  / URLMD5 and available genuine group components. It does NOT
  train or export group keys.
- Remote cleanup uses a ONE-LINE SSH shell command targeting only
  the two new /tmp metadata backup copies and rmdir of their
  UUID folder. No recursive deletion, no live DB modification.
- tests/test_verify_wp3_copied_lyrion_sqlite.py and
  tests/create_wp3_metadata_ci_fixture.py cover synthetic SQLite,
  privacy, and the actual Windows PS5.1/PS7 Python-file invocation
  without any SSH. Real remote execution is not CI tested.

Keep private copies private; share only anonymized aggregate output.
A blocked group-disjoint holdout is valid and must not be bypassed
by file path guessing, lax splits or claiming teacher improvement.
No new audio scan, service restart, main merge or PR #16 edits.


## 30 October 2026: second real Windows run and BusyBox newline fix

User inspected the previous leftover Pi temp directory. Both
original SQLite backup files had already been deleted; its
only remaining files were the temporary companions
library.db-shm (32768 bytes) and library.db-wal (0 bytes).
They are NOT the live Cache/library.db. Earlier cleanup failed
rmdir because these two known SQLite-generated companions
remained. They can be deleted explicitly from that one known
UUID directory and then rmdir; never rm -rf or use wildcards.

The user subsequently pulled research branch commit 0218d878
and ran the corrected Windows launcher. The remote script
using PowerShell here-string pipeline to SSH sh -s failed
BEFORE backup operations at its first command with:
sh: set: line 1: illegal option -
This is consistent with Windows PowerShell 5.1 native pipeline
line-ending/CR transfer to BusyBox sh; the exact bytes have not
been independently captured. The failure boundary is the
remote multi-line command transport, not the live databases.
No true 100-song group preflight has run yet.

Subsequent repair on the isolated research branch replaces the
entire sh -s pipeline with separate single-line ASCII SSH
commands. The commands use GUID-controlled private /tmp staging
and literal known SQLite source paths; SQLite online .backup
runs via echo-to-sqlite3 -readonly -batch -bail, never an unsafe
raw copy of a live database. Each SSH command checks exit status.
Cleanup explicitly targets this run's two temporary .db names
and each -wal/-shm companion, then nonrecursive rmdir.
The Python 3.15 script-file local validation and original
artist/album/recording-readiness preflight are unchanged.

Automated CI verifies Windows PS5.1/7 syntax and Python
arguments on synthetic metadata. CI cannot reach the private
Pi and cannot certify that the new SSH invocation succeeds
until the operator runs it. Do not claim grouped metric
training or artist-independent similarity gains based on
these engineering checks.


## 30 October 2026: FIRST REAL 100/100 authentic grouped preflight PASS

Operator executed the final read-only Windows PS5.1
prepare_wp3_lyrion_group_sources_windows.ps1 on the research branch
commit 4d4da705 after safely removing only the two previously
observed temporary SQLite WAL/SHM files.

The revised one-line SSH + sqlite3 -readonly online-backup mechanism
succeeded, both private SQLite files were transferred and locally
validated with PRAGMA quick_check. Source inventory (from genuine
private LMS and BlissMixerLab databases, no private tracks uploaded):

- LMS: 79,005 tracks, 6,228 albums;
- Lab: 77,517 track_identity, 76,870 artist identity rows;
- Lab schema lyrion-track-identities-v1 and scan_time 1793339060;
- both SQLite files individually valid, snapshot roots hash shaped;
- original Lyrion SQLite databases untouched, Pi staging cleanup
  reported no error.

The actual stdlib-only four-input source-group preflight reported
status SOURCE_GROUPING_READY_PRIVATE_NO_AUDIO_SCANS, with
ready_for_grouped_study=true, blocking_reason_code=null,
sample_seed=20261029, sample_limit=100,
eligible_essentia_head_population=100, selected_head_pairs=100,
rejected Essentia provenance=0, missing or invalid Bliss23=0,
missing/unverified LMS identities=0, missing artist credits=0,
missing albums=0, paired_tracks_with_verified_lms_artist_album=100.
One recording MBID was absent and assigned the conservative unknown
recording group. The joint artist/album/recording grouping yielded
88 connected components; the fixed split contains 75 train and
25 group-disjoint holdout songs.

Private local source files reside under the already-ignored folder:
D:\LMS\bliss-mood-poc\benchmark-wp3-research-20261030-064618-7f8c43a3\lyrion-metadata-eeedcd9630e04da3a3c046db974b33f8 .
NEVER commit, attach or share either SQLite file. They were created
by separate SQLite online backups, and the preflight checked selected
song LMS IDs and URLMD5 equality; cross-DB point-in-time snapshot
atomicity and live scan/root freshness are not independently proven.

**Important scientific qualification:** This is **source provenance
and feasible group-disjoint split readiness**, not a finished model
evaluation. The same 100 songs had already been inspected in 3,289
exploratory correlations, including selected 16 high-effect pairs.
Therefore the 25 group-disjoint songs are NOT an untouched
confirmatory human-similarity test set if any experimental choices
were made using the preceding whole-cohort results. Teacher scores
are proxy targets, not verified human musical similarity ratings.
Do not report an unbiased external test set or an improved General
Metric merely because the grouped teacher code runs.

Next execution can reuse the *existing* script
scripts/build_wp3_research_db_windows.ps1 with both explicit
LYRION_REPEAT_SNAPSHOT_DB and LYRION_LIBRARY_DB pointing at the
two known private Windows copies, and explicit local Bliss and
native Essentia feature DB. That script runs a fresh no-write
preflight, builds a NEW private grouped research SQLite without
overwriting the previous group-free WP3 DB, and invokes the
experimental train-only WP3 teacher-study using the existing
Python 3.15 plus pinned venv, if the grouping still passes.
No fresh audio decode, ONNX scan, service restart or production
deployment is involved. Report only the resulting anonymized
aggregate, not private source SQLite or group identities.


## Metadata provenance source discovery

The existing plugin source
[BlissMixerLab/RepeatIdentitySnapshot.pm](https://github.com/chrober/lms-blissmixer-lab/blob/main/BlissMixerLab/RepeatIdentitySnapshot.pm)
creates artist-repeat-identities.sqlite under
Slim::Utils::OSDetect::dirsFor('cache') / BlissMixerLab, conditional
on the plugin's prepare() routine and a valid LMS last-scan/root
identity. The Pi cache root and actual snapshot were verified and
transferred privately on 30 October 2026; this general dynamic-path
rule still applies on any other host. The LMS library SQLite
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
