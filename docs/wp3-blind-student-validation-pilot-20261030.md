# WP3-R6: BLINDED original-Bliss versus MoodTheme-student pilot (30 October 2026)

> **SUPERSEDED AS IMMEDIATE NEXT STEP — 30 OCT 2026:** The user explicitly requested that all 240 new songs be analyzed with the **original Essentia C++ backend**, including Genre87/MoodTheme56 and pooled EffNet1280D, before deciding on narrower listening-pair diagnostics. The optional 24-pair Bliss-only student blind pilot documented below remains implemented but has **NOT been executed**; it is now deferred. Follow the [frozen 240-song Essentia source and evaluation protocol](wp3-r6-native-240-essentia-protocol-20261030.md) and use the new staged [Windows PowerShell native 240 launcher](../scripts/run_wp3_r6_native_240_windows.ps1). The new 240 teacher outputs are **NOT** available yet; teacher agreement is NOT human perceptual similarity. Original source-identity validation, private data rules, license restrictions, General/Personal workstream separation still apply. Historical instructions below describe a previous optional pilot, not the current authorization.


## Scientific motivation and original evidence

WP3's **first** authentic 100-song grouped teacher-only experiment
is already complete. The original Bliss23 Euclidean distances had
Spearman 0.442049 to Essentia MoodTheme56 pseudo-teacher distances;
train-only StandardScaler + Ridge(alpha=10) Bliss-only student
geometry reached 0.540662 on the 25-song group-heldout development
split. That improvement **does NOT establish** human perceptual or
general-metric quality. The old 25-song "holdout" had been part of
earlier same-cohort exploratory analysis. The teacher's upstream
training overlap and head numerical validation remain unresolved.
[Full completed result](wp3-real-grouped-teacher-study-results-20261030.md).

## New verified 240-song metadata-only cohort: first real operator PASS

User ran the actual Windows PowerShell 5.1
`scripts/prepare_wp3_independent_cohort_windows.ps1` with their
existing private Bliss23 database, copied authentic LMS library and
BlissMixerLab artist snapshot, and their **grouped**, READY 100-song
research DB. Preflight **and** exclusive private manifest creation
reported identical non-identifying results:

- status: `NEW_SOURCE_DISJOINT_BLISS_COHORT_PROPOSED_NOT_EVALUATED`;
- **240** new songs, **100** prior research songs excluded;
- **16 Tempo/MeanSpectralCentroid quartile cells × exactly 15 songs**;
- unique valid Bliss23 for all 240; no common credited artist
  (including collaborations), verified album or known recording
  MusicBrainz ID with the original 100; no mutual sharing of these
  identities across the selected 240 within the copied data;
- scanner selection diagnostics: 77,517 unique-key snapshot rows,
  10,064 without unique valid Bliss23, 12,374 overlapping earlier
  artist/album/recording identity, 1,186 missing or invalid recording
  MBID, 725 unverified artists. These are **sequential exclusion
  categories**, not claims about all disjoint universe counts.
- explicit `essentia_on_new_songs_available=false` and
  `human_similarity_evaluated=false`. No ONNX, audio scan, Lyrion
  API/queue or plugin change occurred.
- private manifest: `benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc/private-independent-cohort.json`,
  locally ignored, never upload/commit.

These 240 independent songs still have possible upstream pretrained
teacher overlap and incorrect/uncredited identities, and no
genre-distribution guarantee. Diversity was sampled from **two**
Bliss feature quartiles, not musically validated strata. The copied
LMS scan/root fingerprints were not compared against live state.
This is independence **under the available source metadata only**.

## R6 implementation: optional label-free blind pair proposal

This code now provides a **reproducible optional blinded review
preparation**, with no actual listening performed. Scripts:

- [R6 Python 3.15 research runner](../scripts/prepare_wp3_blinded_bliss_student_pilot.py)
- [Single-block Windows PowerShell 5.1/7 entrypoint](../scripts/prepare_wp3_blinded_bliss_student_pilot_windows.ps1)
- [Synthetic-only tests](../tests/test_prepare_wp3_blinded_bliss_student_pilot.py)
- [Frozen, model-parameter-free specification](../research/wp3-moodtheme-student-candidate-v1.json)

Research inputs (read-only, copied/private local):
the **genuine first 100-song group-READY research SQLite** containing
Bliss23 and Essentia MoodTheme56 teacher features, original Bliss
TracksV2 SQLite, copied LMS library + BlissMixerLab artist identity
SQLite, the exact independently selected private 240-song manifest
above, and the frozen candidate spec. The Python script **repeats the
entire previous source-grounded independent-cohort selection** for
240 songs and checks the private manifest equals this re-derivation.
Any identity/source drift, missing key, invalid feature, changed frozen
Ridge hyperparameter, unexpected teacher-head validation status,
non-ready prior cohort, or overlap blocks the study, rather than
using guessed provenance.

**Fitting:** To avoid *any* new-cohort target/label leakage, the
StandardScaler and Ridge(`alpha=10`) are fitted solely on the
**100 prior development songs**, not the new 240. This deliberately
*refits* the fixed architectural hypothesis on all prior 100, including
the old 25-song group holdout (because the new cohort is the
subsequent independent proposed evaluation domain). As a result,
those old 25 must **never be described again as a heldout quality
evaluation for these fitted parameters**. No new music or Essentia
inference occurs; only the new Bliss23 vectors enter student inference.
Ridge predicts 56D teacher *pseudo*-scores; Euclidean distance between
predicted vectors defines the student proxy.

**Frozen optional diagnostic pair selection:** Compute original
Bliss23 Euclidean and student 56D Euclidean distances for each
unordered pair of 240 candidate songs (**28,680** total pairs), using
two within-pool ranks, **not** comparing incompatible distance scales.
With fixed seed `20261030`, choose **24** pairs, **48 distinct songs**,
and one appearance per song: 6 where original Bliss ranks the pair
markedly closer than student, 6 in the reverse direction, and **12
uniform-seeded random controls**. Randomize pair order and
left/right presentation; never expose method, rank, score or stratum
inside the blind review CSV. No use of teacher outputs or human
labels from new songs for selection. No fitted threshold, classifier,
personal model or score calibration.

**IMPORTANT SAMPLING WARNING:** 12/24 pairs are intentionally
selected for model disagreements, so this 24-pair pilot is an
*informative diagnostic*, **NOT** a representative unbiased estimate
of population-level similarity quality. The random-control
12-pair subset is also too small to establish generalization.
Review labels, if later voluntarily supplied, must be recorded
*before* opening the sealed selection audit; evaluate disagreement
strata separately, note multiple hypotheses and subject/pair
dependence. Quality evidence for WP1/WP2/WP3 still requires a
larger preregistered independently scored set.

**Private output**, always created in a fresh exclusive
`benchmark-wp3-blind-student-pilot-*/` ignored directory:

1. `private-blind-pairs.csv` — 24 pair IDs, private track filenames,
   blank `similarity_0_to_5` and `comments`. This is a **review
   proposal**, not already assigned listener ratings.
2. `private-frozen-student.json` — fitted StandardScaler mean/scale
   and 56×23 Ridge coefficient matrix plus intercept, pinned
   original development DB hash and frozen-spec SHA256. **PRIVATE,
   derived from user's library, not a shipping production model**.
3. `private-sealed-selection-audit.json` — method-specific
   distances, ranks, stratification and track identifiers. Keep
   **SEALED** until any future human reviews are recorded and
   frozen; never use it to decide the answers.
4. **Only anonymized counts/status to stdout.** None of the above
   files should be uploaded, committed, emailed or logged to CI.

No Lyrion queue is changed; no audio decoded; no mandatory listening
is initiated. A later opt-in Lyrion playback workflow could reuse
existing skill-backed PS queue integration, but it requires a
separate decision and should never queue songs automatically.

## Real execution and evidence status

**As of implementation on 30 October 2026, no actual R6 blinded
pilot was executed on the user's private 240 songs.**
Only the earlier R5 240-song selector was executed and its aggregate
was provided. CI runs entirely with synthetic source-shaped data.
The next safe local operator step, **if desired**, is to pull the
research branch in Windows PowerShell and run the full script
`scripts/prepare_wp3_blinded_bliss_student_pilot_windows.ps1`.
Share **only stdout**; never attach the three private files.
This prepares optional blinded comparisons, not scientific proof.

## Inference boundaries and three-workstream design

The blind pilot compares **original Bliss** versus the
**frozen WP3 teacher-distilled Bliss-only student**. On the new
240 songs, no independently computed Essentia Genre/Mood or 1280D
embeddings exist yet, so **WP1 full alternate metric comparison
cannot be truthfully computed without new audio inference**.
Do not invent WP1 vectors. Neither the original Essence teacher
outputs nor its trained history are independent human truth.

WP1 General Metric remains mandatory and usable without personal
preferences. WP2 personalized learning and calibrated 0–100%
General/Personal blending are separate. No gains are claimed for
either. Do not introduce mandatory new listening, ONNX scans,
production deployment, LMS restarts, adaptive workers changes,
new libraries or PR #16/main modifications.
