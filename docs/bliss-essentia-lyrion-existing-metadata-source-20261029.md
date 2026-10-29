# Existing Lyrion metadata for Bliss / Essentia research (2026-10-29)

> **NEW PREFERRED WP3 RUNNER / 29 October 2026:** User elected to stop entering unknown Essentia/Lyrion SQLite paths manually; [the new consolidated private research database builder](../scripts/build_wp3_research_db.py) and [standalone Windows Python 3.15 entrypoint](../scripts/build_wp3_research_db_windows.ps1) reuse documented existing local Bliss and native 100-song Essentia sources. The old four-DB grouped runner below is preserved for reproducibility but is no longer the preferred onboarding step. Building the private feature SQLite does not demand inaccessible Lyrion artist-repeat or library metadata: if the two optional identity sources are unavailable, genuine group-disjoint training remains BLOCKED with no invented IDs. The new one-DB grouped study path is enabled only once full, authentic artist/album/recording provenance passes. See [full single-DB contract](wp3-consolidated-research-sqlite-20261029.md).


> **Windows PowerShell 5.1 runtime quoting fix (29 October 2026):** The user's first attempt after selecting Python 3.15 failed **before reading any data**: PowerShell's native argument forwarding removed the nested double quotes in `python -c 'import sys; print(str(sys.version_info.major) + "." + ... )'`, yielding `SyntaxError`. The Python 3.15 installation is correct and does not need reinstalling. The one-block launcher now obtains the version with `python --version` and regex-checks 3.15 without quoted Python string literals. Its later scientific-package check uses a quote-free `python -c` argument. The read-only source preflight passes its list of arguments via explicit PowerShell variable splatting. The dedicated WP3 CI now **executes** this exact launcher runtime path on Windows PowerShell **5.1** and **7**, rather than only parser-validating the script. The existing four-source real-data preflight has **not yet been executed on the user's local databases** as of this change. Latest bugfix is isolated on `feat/general-pairwise-similarity-research`; no PR #16, main, Python runtime installations, native scans, or personal song data were changed.


> **Current interpreter policy (29 October 2026):** The user explicitly selected **Python 3.15 only**. The full Windows launcher uses the existing `python` interpreter (requires version 3.15) for BOTH the standard-library no-write source preflight and the subsequent numerical WP3 teacher development study. It creates an isolated **Python 3.15** venv and uses [the new pinned 3.15 statistical requirements](../research/requirements-wp3-py315.txt): NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, joblib 1.5.2 and threadpoolctl 3.6.0. These have publicly available Python 3.15 binary Windows packages; cross-platform synthetic CI runs with Python 3.15. **No 3.13 interpreter, alternate Python installation, runtime bootstrap or fallback to 3.13 is allowed.** The original 3.13 research requirements remain an older historical reproducibility record only. Source availability and real paired-data research results have not been independently checked on the user's machine.






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
separate detached worktree, existing Python 3.15 verification, isolated
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
