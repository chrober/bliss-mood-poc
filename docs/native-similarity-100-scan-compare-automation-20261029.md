# Native same-100 scan → compare automation (2026-10-29)

> **29.10.2026 – AUSFÜHRUNG ABGESCHLOSSEN:** Der reale native 100-Song-Scan und Compare wurden vom Nutzer mit anonymisiertem Ergebnisbericht `PASS_EXPLORATORY_TOLERANCES` dokumentiert. Siehe [Real Native Results](native-similarity-100-real-results-20261029.md). **Die nachfolgenden One-Command-Launcher-Anleitungen sind nur historische Reproduktionsdokumentation. Bitte nicht erneut gegen die bestehenden privaten Ausgabepfade starten.** Der nächste Forschungsabschnitt ist die allgemeine untrainierte Metrik.


**Scope:** continuation of the **already successful** 100/100 Windows preflight.
No new `prepare`, no new cohort, no modifications to PR #16, original
SQLite, private ratings, original embeddings or source music. General
musical similarity is the primary research goal; the 100-song comparison
is a **technical backend-continuity gate**, not a metric-selection study.

## Implementation

- `scripts/bootstrap_native_similarity_scan_compare.ps1` updates the
  isolated clean worktree only (never switches the PR #16 checkout).
- It reuses the pinned successful GitHub scanner artifact from workflow
  `40758319812` (downloading it only if absent); verifies its EXE SHA,
  BUILD.txt, SHA256SUMS.txt, GitHub run/source SHA; reuses the already
  installed private Essentia C++ worker, checking the **complete** native
  DLL/EXE inventory against worker-dependencies.json, including sizes,
  filenames and SHA256. It does **not** download or redistribute a native
  C++ bundle.
- It checks the existing preflight provenance, fixed manifest SHA
  `f4d359fa1187f4a2626c14b7abe4a34f5d2143ec014c1b9e7f01545cc53e0b77`,
  old DB SHA `c8bcf43049bd3c3abeccbb3518969ad357153313928b00f59a248c8566e09865`,
  model hashes, exact scanner and worker SHAs.
- `scripts/verify_native_similarity_frozen_inputs.py` reuses the
  existing bridge's read-only cohort/embedding/model/audio validators and
  checks that every manifest key and 100 audio SHA256s still match.
  **This is a pre-scan integrity check of the *existing* plan, NOT a
  second preflight or a new cohort selection.** No files are written.
- The existing `run_native_similarity_cohort.ps1 -Step scan` invokes
  `scan-features --tracks-file --audio-backend essentia` with Genre,
  Mood, Voice, 1280D pooled embeddings, static `--workers auto`,
  `--threads 1` and `--max-errors 3`. It writes only a previously
  empty private native SQLite/embedding destination.
- The existing `-Step compare` invokes the tested Python bridge:
  verifies identities, SHA256, 87D/56D, 2D voice, 1280D, patch
  counts, all five measures over **4,950** pairs, and the immutable
  existing **12/11** pilot labels. It writes a **new private aggregate**
  `aggregate-native-cohort-comparison.json`.
- Existing native DB/WAL/journal/embedding files and existing result
  folder block normal execution. `-Mode CompareOnly` is allowed after
  an independently inspected complete native scan; it never starts
  another scan. A failed comparison is not silently retried.
- Diagnostic thresholds (score drift 0.001, song embedding cosine 0.999)
  are **exploratory**, not a certified Essentia reference equivalence.

## First launch: paste exactly this PowerShell block

The currently installed isolated worktree predates this new script, so
one safe update is required. This block never calls the previous
`bootstrap_native_similarity_preflight.ps1`.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    $Worktree = 'D:\LMS\bliss-mood-native-bridge'
    $Branch = 'feat/native-similarity-cohort-validation'

    & git -C $Repo fetch --no-tags origin $Branch
    if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch bridge branch' }
    $SHA = (& git -C $Repo rev-parse "refs/remotes/origin/$Branch").Trim()
    if ($LASTEXITCODE -ne 0 -or $SHA -notmatch '^[0-9a-f]{40}$') {
        throw 'Cannot resolve bridge SHA'
    }
    if (-not (Test-Path -LiteralPath $Worktree)) {
        & git -C $Repo worktree add --detach $Worktree $SHA
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create isolated worktree' }
    } else {
        $Dirty = @(& git -C $Worktree status --porcelain --untracked-files=normal |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($LASTEXITCODE -ne 0 -or $Dirty.Count -gt 0) {
            throw 'Existing isolated worktree is not clean'
        }
        & git -C $Worktree checkout --detach $SHA
        if ($LASTEXITCODE -ne 0) { throw 'Cannot update isolated worktree' }
    }
    & (Join-Path $Worktree 'scripts\bootstrap_native_similarity_scan_compare.ps1')
    if (-not $?) { throw 'Scan/compare automation did not finish' }
}
```

## Subsequent invocations

```powershell
& 'D:\LMS\bliss-mood-native-bridge\scripts\bootstrap_native_similarity_scan_compare.ps1'
```

The script fetches new bridge commits, checks for a clean isolated
worktree, re-enters the newly checked-out version, validates inputs,
and performs scan+compare if both output destinations are still unused.
If native output already exists, it **stops** rather than redoing the
scan. After inspection of a fully completed native scan, compare-only:

```powershell
& 'D:\LMS\bliss-mood-native-bridge\scripts\bootstrap_native_similarity_scan_compare.ps1' -Mode CompareOnly
```

Do not use CompareOnly to imply an interrupted scan was complete.
The comparison independently rejects incomplete/mismatched tracks,
embeddings, voices, audio hashes, model identities or patches.

## Status / evidence boundary

- **Known from user's local console:** 29 Oct preflight PASS 100/100.
- **Repository implementation:** new safe orchestration and frozen-input
  recheck are source-committed, with synthetic Linux/Windows CI.
- **Not yet observed in the connected GitHub environment:** real native
  scan, private 100-song native SQLite/embeddings, actual 4,950-pair
  ranking output, or real 12/11 new-backend correlations.
  Those run on the user's Windows machine and remain private.
- The anonymized aggregate is expected at
  `D:\LMS\bliss-mood-poc\benchmark-native-similarity-comparison-20261029\aggregate-native-cohort-comparison.json`.
  It may be shared for scientific interpretation; **do not upload**
  manifests, private DBs, model/worker binaries, DLLs, individual
  vectors, audio, CSV ratings, or sealed audit to GitHub.
- Preserve original 29-Oct plan/provenance unchanged. The scanner
  and C++ DLL bundle are **NOT approved for public distribution**,
  including 17 missing installed third-party license notices.

## Scientific handback after successful compare

Treat same-song numerical drift and rank continuity as engineering
qualification only. Keep the 12/11 human comparisons exploratory,
not a source of fitted fusion weights. Then evaluate an
**unpersonalized general metric** using independent data splits and
source-appropriate MTT (tag/genre), FMA (music metadata/genre) and
DEAM (arousal/valence) evidence. Avoid label leakage, cross-dataset
ground-truth conflation, and false independence of the 4,950 pairs.
An optional personal metric is strictly downstream.
