# Reproducible 100-song Rust-v5 -> native Essentia similarity bridge (2026-10-29)

**Research-only.** This work is on feat/native-similarity-cohort-validation,
based on main after PR #20/#22. **DO NOT merge to PR #16**, rewrite the
original user-rated CSV, retrain a personal model, delete saved sidecars,
start a whole-library scan or publish native dependencies. All user-local
music, hearing data, manifests, DBs and vectors stay off GitHub.

## Verified technical context

- main at initial handover: af38df464ef2c97aac98c728f684da189e6525c0.
- PR #16 is open/draft at 2204ec91d8d8a773872f266397b0656178b481ee.
  It is *not* based on the newly merged main native feature backend.
- Qualified Windows scanner: workflow 40758319812, source
  da8fecee23930c2e52abcb473a62b8178b2d5474.
  Use artifact bliss-mood-windows-x64. SHA256 of bliss-mood.exe is
  00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d.
  Confirm BUILD.txt, SHA256SUMS.txt, Get-FileHash and the exact source
  chain. The ZIP hash is NOT the EXE hash.
- Separate native Windows C++ reference/scan gate 40760885061 passed
  after PR #22 pinned its external similarity evaluator snapshot.
  This does not prove parity on the local 100-song library.
- Current scanner native frontend identity is
  experimental-essentia-cpp-dsp-v1-unvalidated; the old library
  uses experimental-essentia-audio-v5-f32-src-ratio-unvalidated.
  Keep them separate. No conversion or reinterpretation of
  backend fingerprints is allowed.
- Native kit redistribution remains BLOCKED, notably due to 17
  missing installed dependency license notices. Local analysis is
  separate from release approval.

## What was implemented

1. scripts/native_similarity_cohort_bridge.py, subcommand prepare:
   strictly read-only open the existing 100-song schema-v3 Rust-v5
   Genre 87D / Mood 56D SQLite DB and exactly 100 matching
   1280D per-song exports; reject missing/extra/fingerprint/patch
   inconsistencies, verify ordered label metadata and exact
   existing official ONNX weights, hash all 100 source audio files,
   pin scanner EXE SHA256 and native-worker EXE SHA256.
   Only AFTER all checks pass, create a brand-new ignored private
   folder with exactly 100 source-relative track keys in
   exact-100-tracks.txt (no random re-selection), provenance.json
   (SHA256 of inputs, models, metadata and manifest), and an
   initially empty native-embeddings/ folder.
2. scripts/run_native_similarity_cohort.ps1, step scan:
   rechecks scanner/worker/model/manifest hashes and uses
   scan-features --tracks-file with original Essentia C++ DSP,
   Mood/Theme, Genre, Voice and normalized pooled 1280D
   embeddings, --workers auto (STATIC once at start),
   --threads 1 and --max-errors 3. A new native SQLite and
   new embedding files are the only scanner writes.
   It refuses to blindly run over an existing native DB.
3. compare: verifies same exact 100 song keys, source SHA,
   patch counts, exact shared ONNX weights and ordered
   classification labels, distinct backend model keys,
   native worker SHA, 100 voice outputs, all 100 embeddings,
   87D/56D maximum/mean per-class differences and 1280D
   per-song cosine/component drift. It recomputes the original
   five A/B similarity methods for all 4,950 unordered song
   pairs and reports old/native Spearman rank stability plus
   maximum score drift. Default diagnostic thresholds are
   max classifier component difference 0.001 and minimum
   old/native song-embedding cosine 0.999; these are explicitly
   EXPLORATORY review gates, not independently qualified
   reference-equivalence certifications.
4. compare optionally reads the original local 12-pair ratings
   and sealed score audit. It verifies exact pair order and
   identity and reproduces the previously sealed OLD scores
   before computing old/new 5-model × 4-rating Spearman
   correlations on all twelve and eleven pairs excluding
   the human-flagged nonmusic pair #10.
   No original ratings, scores, notes or audio are changed;
   none is included in the aggregate report.

All output JSON statistics are aggregate, hashed or numbered
without original song names, paths, raw notes or per-song
vectors. The private manifest contains real source-relative
song identities, MUST be kept only on the local workstation.
Synthetic Linux and Windows CI uses no user music.

## Corrected frozen-cohort selection (2026-10-29)

The first real local preflight reported
`baseline_feature_cohort: Unexpected head, preprocessing or model identity`.
**Root cause in the bridge design:** the reader assumed that every
`feature_tracks` row in the *historical* benchmark SQLite
belonged to just one exact Rust-v5 Genre/Mood pair. PR #16's
original reviewed 100-song pilot instead used its deterministic
dominant-model cohort selection (count descending, stable model
fingerprint tiebreak), then the exact joined Genre+Mood keys
in binary path order with seed 20261021. The actual database's
additional historical/other-head rows must not be silently
interpreted as a corrupt 100-song cohort.

The reader now mirrors PR #16's original eligible dominant
Genre+Mood selection and exact joined 100 keys, then validates
the independently preserved **100 encrypted-name JSON
embeddings**, source audio fingerprints, ONNX weights, class
order and both classification heads. Alternative DSP
preprocessing on a dominant cohort, different fingerprint
definitions, invalid feature rows, changed 100-song membership
or extraneous native output rows remain **hard errors**.
No previous user files are modified. Synthetic regression
tests cover historical voice/earlier-backend rows and
fail-closed rejection of a dominant wrong frontend.
Linux and Windows regression tests passed in
[workflow 40873290274](https://github.com/chrober/bliss-mood-poc/actions/runs/40873290274).

The already installed bootstrap updates the *separate,
clean* worktree automatically. To retry the preflight,
**do not** repeat the manual checkout or downloads; run:

~~~powershell
& 'D:\LMS\bliss-mood-native-bridge\scripts\bootstrap_native_similarity_preflight.ps1'
~~~

Its `prepare` step never starts native audio inference.
If another named stage fails, fix that specific invariant
before attempting `scan`. Do not delete or bypass
older research records to force a successful audit.

## Preferred fully automatic Windows preflight (2026-10-29 update)

The first real local preflight failed with only "ValueError";
there is not enough information to identify its root cause.
The bridge now prints **named safe checkpoints**:
baseline_feature_cohort, baseline_embedding_exports,
onnx_model_weights_and_class_metadata,
verified_scanner_and_native_worker and numbered
audio_sha256_001_of_100 .. audio_sha256_100_of_100.
It reports an allowlisted reason or an exception category
without disclosing private track paths. No tracebacks with user
song names, audio data or rating comments are printed.

**Preferred:** scripts/bootstrap_native_similarity_preflight.ps1
automatically fetches and fast-forwards the **separate clean
worktree** to the latest remote bridge branch (never touches
the existing PR #16 checkout), checks the pinned GitHub
workflow provenance, downloads the verified scanner if missing,
reuses the old download if already correct, verifies BUILD.txt
and SHA256SUMS.txt, and uses the known local:
D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe
with its SHA256-verified worker-dependencies.json full native
DLL inventory. It also uses the verified local ONNX files, old
100-song sidecar, old 100 embedding JSONs and documented
\\192.168.1.100\music source root. It performs **prepare only**,
NEVER runs a real scan or overwrites the original data. No
automatic native-kit distribution; missing local worker is
reported as a prerequisite, not secretly downloaded.

One-time launcher to obtain the **new** automation file
in the already created dedicated worktree:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    $Worktree = 'D:\LMS\bliss-mood-native-bridge'
    $Branch = 'feat/native-similarity-cohort-validation'
    & git -C $Repo fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    $Dirty = @(& git -C $Worktree status --porcelain --untracked-files=normal)
    if ($LASTEXITCODE -ne 0 -or $Dirty.Count -ne 0) {
        throw 'Dedicated worktree is not clean; no automatic checkout.'
    }
    & git -C $Worktree checkout --detach "origin/$Branch"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot update isolated worktree' }
    & (Join-Path $Worktree 'scripts\bootstrap_native_similarity_preflight.ps1')
    if (-not $?) { throw 'Automated preflight did not pass' }
}
~~~

After the one-time launcher, future preflight invocations
can use only:

~~~powershell
& 'D:\LMS\bliss-mood-native-bridge\scripts\bootstrap_native_similarity_preflight.ps1'
~~~

All scripts are fail-closed. Never continue to Step scan
if the verified local preflight is not green. An existing
private output folder is protected from any overwrite;
review it before deciding whether a fresh named output
directory is required.

## Safe local workflow: three separate stages

Keep the existing PR #16 checkout (for example
D:\LMS\bliss-mood-poc) intact. A **separate worktree**
avoids accidentally changing PR #16:

PowerShell (one-time setup, from a trusted local session):

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $OldRepo = 'D:\LMS\bliss-mood-poc'
    $ToolRepo = 'D:\LMS\bliss-mood-native-bridge'
    if (Test-Path -LiteralPath $ToolRepo) {
        throw 'Tool worktree already exists; inspect it instead of overwriting.'
    }
    & git -C $OldRepo fetch origin feat/native-similarity-cohort-validation
    if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' }
    & git -C $OldRepo worktree add --detach $ToolRepo origin/feat/native-similarity-cohort-validation
    if ($LASTEXITCODE -ne 0) { throw 'git worktree add failed' }
}
~~~

Download the **scanner only** from the pinned successful workflow
into a new, untracked private directory; do not mistake this
for the separately provisioned original native worker:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $BinDir = 'D:\LMS\bliss-mood-private\verified-scanner-40758319812'
    if (Test-Path -LiteralPath $BinDir) {
        throw 'Binary output folder already exists; inspect it before reuse.'
    }
    & gh run download 40758319812 --repo chrober/bliss-mood-poc --name bliss-mood-windows-x64 --dir $BinDir
    if ($LASTEXITCODE -ne 0) { throw 'Verified workflow artifact download failed' }
    $Exe = Join-Path $BinDir 'bliss-mood.exe'
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
        throw 'Expected scanner EXE not found. Inspect extracted artifact layout.'
    }
    $Digest = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Digest -cne '00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d') {
        throw 'Executable hash does not match verified build'
    }
    Write-Host 'Scanner binary hash matches pinned workflow build.'
    Get-Content -LiteralPath (Join-Path $BinDir 'BUILD.txt')
    Get-Content -LiteralPath (Join-Path $BinDir 'SHA256SUMS.txt')
}
~~~

Set these **three machine-dependent paths** on your Windows system;
the first two cannot safely be inferred from the repository:

- AudioRoot: the actual Windows-accessible source root for the
  original TracksV2.File relative paths (for instance your
  mounted NAS share). It must contain the same bytes as
  the original 100-song Rust-v5 scan.
- NativeWorker: the already-provisioned, trusted original
  Essentia C++ worker EXE and its private native DLL dependencies.
  This is NOT the Rust scanner EXE.
- ModelsDir: the local directory containing the original
  official ONNX weights and JSON label files for all three heads.

The following block runs **prepare only** (NO audio analysis):

~~~powershell
& {
    $ErrorActionPreference = 'Stop'

    $Runner = 'D:\LMS\bliss-mood-native-bridge\scripts\run_native_similarity_cohort.ps1'
    $AudioRoot = 'REPLACE_WITH_WINDOWS_MUSIC_ROOT'
    $NativeWorker = 'REPLACE_WITH_LOCAL_NATIVE_WORKER_EXE'
    $ModelsDir = 'D:\LMS\bliss-mood-poc\models'
    $Scanner = 'D:\LMS\bliss-mood-private\verified-scanner-40758319812\bliss-mood.exe'

    if ($AudioRoot -like 'REPLACE_*' -or $NativeWorker -like 'REPLACE_*') {
        throw 'Configure real trusted audio root and native Essentia worker first'
    }

    & $Runner -Step prepare -AudioRoot $AudioRoot -NativeWorker $NativeWorker -ModelsDir $ModelsDir -ScannerExe $Scanner
    if (-not $?) { throw 'Native cohort preflight did not pass' }
}
~~~

After independently reviewing the prepare JSON (exactly 100 tracks,
original hashes, correct scanner and model fingerprints), run
the same block with Step changed to scan, and after scan success
run it with Step changed to compare. Every stage is separately
invoked; it is deliberately NOT an automatic three-stage
pipeline. The runner rejects a stale manifest, changed
scanner/worker/ONNX hashes, missing originals and existing
output folders. A failed or interrupted scan is not
automatically retried.

**Expected new private files:**

- D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029\
  exact-100-tracks.txt, provenance.json, native-features.sqlite,
  native-embeddings/
- D:\LMS\bliss-mood-poc\benchmark-native-similarity-comparison-20261029\
  aggregate-native-cohort-comparison.json

The second report can be shared for interpretation if desired;
it contains no private song identities. The first manifest,
private baseline and new feature databases, embeddings, human CSV,
sealed audit and original audio must NOT be uploaded.

## Scope and research interpretation

- The old local 100 Rust-v5 songs have already been scanned.
  New native feature extraction has **NOT** run until the user
  executes scan with the original private library and worker.
- Same-song numerical/parity gates are **technical equivalence
  checks**, not music preference benchmarks.
- All 4,950 pairs depend on just 100 songs. Their
  old/native rank correlation measures representation
  continuity, **not** independent evidence of human
  musical-similarity quality.
- Keep MTT/FMA/DEAM reference dataset splits and leakage
  caveats; preserve previous 12 ratings as diagnostic
  evidence only. No new mandatory manual listening test.
- Avoid optimizing general similarity-fusion coefficients
  on the same twelve human-rated pairs.
- Separate the universal general metric from optional
  personalized metric learning and the personal 0-100%
  mixing control.
- Do not reopen adaptive worker tuning or PR #19/Issue #21.
