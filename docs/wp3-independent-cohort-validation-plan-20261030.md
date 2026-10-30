# WP3 R5: new independent cohort and frozen perceptual-evaluation protocol (30 October 2026)

## Decision and source evidence

The **first real 100-song WP3 teacher study is finished**, with 88
artist/album/recording-connected components, a 75/25 within-run group
holdout, MoodTheme Ridge reconstruction MAE reduction 13.04% over
training-mean and a Spearman teacher-distance proxy improvement from
0.442049 (original Bliss) to 0.540662 (Bliss-only Ridge student).
See [the complete numeric findings](wp3-real-grouped-teacher-study-results-20261030.md).

Those 100 tracks were previously inspected for 3,289 associations
and 16 post-selected relations. The 25 group-disjoint songs therefore
are NOT independent previously unexamined confirmation. Genre improvement
in pair-distance geometry was small (+0.011640). MoodTheme teacher
reconstruction is not evidence of better subjective song similarity.
Two upstream Essentia heads are still explicitly unvalidated against
reference numerical Essentia results. No evidence supports production
weights or a user-facing model deployment.

The next *separate* research activity is to **freeze a candidate
configuration and create a new, as-yet unevaluated source pool**,
without scanning audio or exposing private song data. The frozen
machine-readable candidate is
[research/wp3-moodtheme-student-candidate-v1.json](../research/wp3-moodtheme-student-candidate-v1.json).
It declares only an *architecture* (Bliss23 -> train-fitted StandardScaler
-> Ridge alpha 10 -> 56D MoodTheme pseudo-target geometry -> Euclidean
distances). There is NO persisted fitted scaler, Ridge matrix, calibrated
distance, production plugin, or private audio-dependent model in Git.

## Implemented safe source-disjoint cohort planner

Scripts:

- [Python 3.15 stdlib selector](../scripts/prepare_wp3_independent_cohort.py)
- [self-contained Windows PowerShell launcher](../scripts/prepare_wp3_independent_cohort_windows.ps1)
- [source-shaped synthetic regressions](../tests/test_prepare_wp3_independent_cohort.py)

Input sources are **existing private local snapshots**, all opened
with SQLite mode=ro, query_only: original Bliss TracksV2, Lyrion
library.db, BlissMixerLab artist-repeat-identities.sqlite, and the
NEW grouped WP3 research SQLite from the completed first experiment
(2026-10-30 09:16). Do not substitute the earlier feature-only
research SQLite lacking verified groups. Input paths in the standalone
PowerShell launcher are the exact paths from the user's successful
previous Windows run; a different host must be explicitly investigated.

Algorithm and fail-closed guards:

1. Require old research DB schema version and READY group provenance,
   24+ existing old song keys and nonempty artist, album and recording
   grouping columns; verify all old selected songs still match genuine
   snapshot LMS IDs, URLMD5 and library album/audio membership.
2. Enumerate exact metadata snapshot keys, verify matching current
   copied Lyrion tracks IDs/URLMD5, unique valid upstream Bliss 23D
   vector and ARTIST/TRACKARTIST canonical keys; do **not** infer
   album, artist or duplicates from folder/file names.
3. Reject any candidate sharing an **exact key, credited artist
   (including collaborations), LMS album ID, or valid recording MBID**
   with the original 100 studied tracks. Reject missing/invalid
   recording MBIDs among NEW candidates instead of silently
   assuming independence. Reject unsupported schemas and stale
   selected old snapshot IDs/URLMD5; this cannot independently
   validate latest live LMS scan/root fingerprints or historical
   pretraining-domain overlap.
4. Select **240** new songs by a deterministic seeded SHA256 order
   (seed 20261030) and round-robin across **4 × 4 quartile cells**
   of existing Bliss Tempo and MeanSpectralCentroid; these are
   limited sampling diversity proxies, **not** music genre labels.
   Allow *no shared credited artists, albums or known recordings
   among the 240 selected songs either*. Fail closed rather than
   quietly lowering sample count or admitting overlapping groups.
5. The preflight prints only non-identifying aggregate counts.
   The second exclusive creation writes exact song keys/LMS IDs
   and source attribution **only inside a new ignored local private
   benchmark-wp3-independent-cohort-*/private-independent-cohort.json**.
   Never commit/upload this manifest, private sources or song features.
   No Essentia scores, new ONNX/decoded audio, human labels, playlist
   mutations, Lyrion web API, SSH, service restarts or plugin installs.

This is **planning only**. A successful run establishes candidate
eligibility and disjointness against the *available current metadata
snapshot*, not a finished or scientifically diverse experiment. Wrong
MusicBrainz IDs, uncredited artists, source updates, nonidentical
decoded audio or teacher pretraining overlaps remain open confounds.

## How to run (Windows PowerShell only)

From the existing research branch with Python 3.15 already installed,
pull only the research branch and run:

    & .\scripts\prepare_wp3_independent_cohort_windows.ps1

For a different research host or source layout use the Python
entrypoint with explicit real database paths. The PowerShell
script validates exact known existing files and the research branch,
runs a no-write preflight, then produces a new UUID-named
private manifest. It neither changes the existing 100-song database
nor requires a new Pi transfer or new audio scan. It is rerunnable
with exclusive new outputs; the manifest is deterministic for an
unchanged source snapshot and fixed seed. Only its **anonymized
stdout aggregate** is appropriate to share back.

## Preregistered next *measurement* gates (not yet executed)

**Source/provenance:** Before running any additional audio analysis,
inspect the candidate aggregate and count group coverage, rare
strata, unknown MBIDs and source freshness. Recheck live scan/root
staleness and snapshot provenance. Confirm metadata reflects
actual source recordings, not just exact file URL identity. Avoid
a new scan unless the operator explicitly authorizes it.

**Independent model fit:** Refitting the MoodTheme candidate on
source-grounded old *development* data only is a separate authorized
operation and must write private parameters with versioned class/
model/preprocessing fingerprints. Never fit a scaler, feature weight,
model selection or threshold on the proposed future evaluation
cohort's teacher scores or human ratings. The frozen candidate JSON
does not contain trained parameters.

**Primary human/perceptual test:** Before any results are inspected,
fix a blinded listening/question protocol and publish code+seed
for sampling, candidate order, human labels, evaluation metrics,
tie handling and source exclusion. Compare the original Bliss
distance against the frozen Bliss-only student, plus independent
WP1 Genre/Mood/embedding/fusion alternatives. Use a valid external
reference or specifically consented listening judgments; no
mandatory new user ratings. A teacher reconstruction proxy may be
recorded as *secondary* context only.

**Statistics:** Pairs/triplets sharing songs or groups are dependent.
Report effects and uncertainty by source/artist/album/recording
cluster, with preregistered comparisons and correction or clear
exploratory labels for multiple candidate searches. Do not report
300 pairwise distances from 25 songs as 300 independent subjects.
Preserve a final truly unseen confirmation set: if evaluator
feedback on this new cohort guides tuning, call it development,
not untouched test evidence.

**Workstream boundaries:** WP1 General Metric remains mandatory
and fully functional with no listener training. WP2 optional
Personal Metric Learning with a calibrated 0–100% influence slider
and strict 100% General fallback is separate, not implied by WP3.
WP3 teacher-distillation is a competing explanatory representation,
not a substitution for either the General or Personal scorer.
No automatic BlissMixerLab production changes, native worker tuning,
new scans, main merge or PR #16 edits.

## Execution status

This repo change implements **cohort selection / leakage screening**
and synthetic integration gates. No real future cohort has yet been
selected by the operator, no new teacher/student weights were trained,
no perceptual comparisons were made, and no new song audio was decoded.
The output is a private planning manifest, not a listening CSV or a
server queue.
