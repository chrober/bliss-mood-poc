# Existing Lyrion metadata for Bliss / Essentia research (2026-10-29)

> **Operator runtime fix, 29 October 2026:** On a real Windows shell, the initial WP3 launcher stopped **before opening any source database** because it required `py -3.13`, while the operator has `python --version = Python 3.15.0`. The preceding `PASS_EXPLORATORY_TOLERANCES` refers only to the independent native backend cohort diagnostic comparison, not WP3 feature relationships. [The corrected launcher](../scripts/run_grouped_bliss_essentia_research_windows.ps1) now uses the available `python` executable (>=3.10, including Python 3.15) for the stdlib-only **no-write** Lyrion/Bliss/Essentia identity and group preflight. It probes **Python 3.13 only AFTER the real four-source/group preflight passes**, because the exact pinned NumPy/SciPy/scikit-learn research environment has been verified on Python 3.13, not Python 3.15. Missing 3.13 produces an actionable message `py install 3.13` (side-by-side), without auto-installing software or claiming the teacher-analysis stage ran. On the operator machine no actual WP3 preflight or real correlations had been observed as of this update; synthetic CI is a separate engineering gate. Avoid insisting that the operator downgrade or remove Python 3.15.


> **Read-only source preflight refinement (29 October 2026):** The group adapter now accepts `--preflight` **without** `--out-groups-private`. It tests the deterministic original Bliss23/Essentia87+56/BlissMixerLab snapshot/Lyrion SQLite overlap and emits only aggregate counts, grouping availability and one machine-readable `blocking_reason_code`; it writes **no** output file and runs with the Python standard library, before any numerical packages are installed. Blockers include `TOO_FEW_VERIFIED_PAIRED_SONGS`, `INCOMPLETE_LYRION_TRACK_ARTIST_ALBUM_IDENTITY`, `NO_GROUP_DISJOINT_HOLDOUT` and `GROUP_DISJOINT_HOLDOUT_TOO_SMALL`. Unsupported source schemas cause a generic, fail-closed error. The snapshot must carry a positive source `lms_scan_time` and a well-formed 64-character `media_roots_identity`; the **current** LMS scan and musicroot identity are still **not independently compared**. The [complete Windows runbook](../scripts/run_grouped_bliss_essentia_research_windows.ps1) now executes this **no-write preflight first, before installing NumPy/SciPy/scikit-learn or producing any private groups**. On a blocker it prints nonidentifying counts and aborts; it never fabricates group identities or launches the teacher study. Synthetic tests cover valid readiness, stale URLMD5, malformed cache metadata, zero independent groups and no-file preflight behavior. No real private library data have been read in CI or by this documentation update.


Research-only source audit. No real private song features or personal ratings
were read, and no real-music correlations or improved similarity metrics are
claimed. Changes remain on the isolated general-pairwise-similarity-research
branch. Draft PR #16, main and related source repositories are unchanged.

## Actual source finding, not a new metadata system

The existing chrober/lms-blissmixer-lab file
BlissMixerLab/RepeatIdentitySnapshot.pm already creates
artist-repeat-identities.sqlite in the plugin cache. It has a
versioned metadata table and the following tables:

- track_identity: exact relative database_file, lms_track_id,
  lms_urlmd5, recording_mbid, original primary contributor data.
- track_artist_identity: zero or more ARTIST and TRACKARTIST
  roles and their canonical artist keys.

The existing Lyrion SQLite library.db tracks table contains
id, urlmd5, musicbrainz_id, album, remote, audio. The
tracks.album to albums.id relationship is documented by the
Lyrion DB reference: https://lyrion.org/reference/database-structure/.
The snapshot source already resolves Lyrion music-root URLs
to the exact relative database_file. We reuse that mapping;
artist/album identity is **not inferred from folders or titles**.

The original Bliss 23D reader uses TracksV2.File, while Essentia
schema-v3 uses feature_tracks.track_file. Their existing exact-key
join can therefore be connected to snapshot database_file, then
to the Lyrion database using the snapshot lms_track_id and
matching urlmd5. This removes the need for a user-maintained
artist/album mapping **if the existing four sources are available
and mutually consistent**.

## Implemented local bridge

The new scripts/derive_lyrion_research_groups.py reads these
four existing sources, all with SQLite mode=ro and query_only:

1. Original Bliss SQLite with the exact ordered 23D feature columns.
2. Original Essentia feature SQLite (Genre87 and Mood56, coherent
   encoder/patch/audio/model provenance).
3. Existing Lab artist-repeat-identities.sqlite.
4. Existing Lyrion SQLite library.db.

Its deterministic sample uses the same seed/limit as the subsequent
local teacher study. For every Bliss+Essentia-eligible sampled song,
it verifies the Lab snapshot schema identity, exact file identity,
track id, urlmd5 and remote/audio eligibility. It looks up actual
album ids and credited artist identifiers. Tracks sharing any artist
credit or collaborative artist are joined into artist-connected
components. Tracks with the same actual album id are grouped
together. Valid MusicBrainz recording UUIDs are grouped by UUID.
All missing or malformed recording UUIDs are **conservatively
assigned to one shared unknown-recording group**: this may force
the research to abort rather than claim duplicate-independent data.

If any otherwise eligible song has no authoritative verified Lyrion
track, artist or album, the grouped study fails closed. It also
refuses a cohort with too few paired recordings, an inadequate
artist/album/recording-disjoint holdout, mixed models or changed
source schemas. No scans, audio or LMS commands are executed.
Outputs are a private mapping file only plus nonidentifying
aggregate counts. Snapshot and Lyrion data are never written.

Caveat: matching the sampled records' track id and urlmd5 does
NOT independently verify the snapshot cache's original music-roots
fingerprint or that the current LMS scan time is identical.
Lyrion MySQL/MariaDB storage is not supported by this SQLite-only
reader. Likewise, a matching historical file key cannot prove
byte-identical Bliss/Essentia audio, and teacher model training
overlap has not been ruled out.

## Complete automated Windows local runbook

See scripts/run_grouped_bliss_essentia_research_windows.ps1.
It is a full directly executable PowerShell wrapper beginning
with ampersand-open-brace and ending with close-brace, with
repository verification, research-branch-only Git fetch,
separate detached worktree, Python 3.13 discovery, isolated
virtual environment, pinned NumPy/SciPy/scikit-learn,
existing source SHA256 before and after, deterministic
metadata generation, aggregate-only teacher study,
non-overwrite outputs and explicit error detection.

Unlike old native experiments, this purely Python read-only
study does **not** need a compiled binary download. The Git
commit SHA is shown, and every source and final aggregate
is SHA256-checked. No private track identities are uploaded.

Required source paths are taken only from explicit local
environment variables LYRION_BLISS_DB, LYRION_FEATURE_DB,
LYRION_REPEAT_SNAPSHOT_DB and LYRION_LIBRARY_DB or from
interactive prompts inside the single script. No assumed
D:\ drive, recursive audio search, Lyrion player queue action
or guessed Raspberry Pi cache location. The user must be
able to access these four SQLite files locally or via
an already-mounted read-only share. The script has not been
executed against the user's machine.

All PRIVATE group keys and any actual personal feature
data must remain on that machine. Do not commit the private
JSON or upload it as a GitHub Actions artifact.

## Evidence and verified blockers

The available GitHub source tree contains the experimental
read-only adapters and synthetic testing code, but no
permissioned real same-song Bliss23/Essentia87/56 data
with validated artist/album groups. A check of the selected
recent synthetic Actions runs 40904671165 and 40899269545
returned no dataset artifacts. An older Windows research
run 39664316069 exposes an executable-only artifact,
not personal song feature vectors. The prior global fusion
MTT replay 40881326086 failed on external archive HTTP
range access, not a metric-quality result.

Previous local native 100-song continuity results and the
closed twelve-rated-pair pilot are valid historical evidence,
but they do not certify the grouping and Bliss 23D overlap
required here. No successful real paired-source correlation,
student-distance advantage or independent perceptual
similarity improvement can be claimed yet.

The latest tests for the source bridge use synthetic but
genuinely schema-shaped Lyrion and BlissMixerLab SQLite
fixtures. They verify collaborations, exact track/md5 match,
album joins, invalid/missing recording IDs, group holdout
availability, source bytes unchanged and output privacy.
The WP3 Windows+Linux CI also parses the full Windows script.
These are engineering tests only.

## Next experiment and gates

1. Verify the four **actual** sources are available on the
   research host, without inventing paths, resuming scans
   or uploading private data. If missing, report which
   source or identity relation is absent; do not fill in
   fake group labels.
2. If the source-derived group bridge passes, use the
   existing run_local_bliss_essentia_teacher_study.py
   for the first real grouped correlation / Ridge / PLS /
   PCA-CCA / Bliss-only teacher-geometry development evidence.
   Use one fixed seed and sample limit in both processes.
3. Inspect group coverage and uncertainty, including
   unknown recording IDs, source/model fingerprints and
   enough independent artists/albums. A too-large unknown
   group is a valid blocker, not a justification to relax
   the holdout silently.
4. Independently validate transformed Bliss-only similarity
   against a separate musical/human reference, not only
   Essentia pseudo-teacher distances. Do not promote
   a metric from teacher reconstruction alone.
5. Continue General Metric and optional Personal Metric
   Learning in parallel. No compulsory new listening,
   native rescans, adaptive worker autotuning or PR #16
   changes.
