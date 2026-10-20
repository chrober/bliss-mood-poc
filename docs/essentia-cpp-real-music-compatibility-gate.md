# Gate: Windows original Essentia C++ versus Rust on real music

**Scope:** PR #17, branch `feat/essentia-cpp-worker-backend`. Goal: demonstrate
numerical and persistence compatibility on an identical **real** selection
of music files, then merge #17 to main **only after** a green review of the
results. Further *similarity metric* research continues separately in draft
PR #16 after its branch is updated to include the merged backend.

## Proven in CI — not the same as this gate

On 2026-10-20, the genuine Windows-x64 CLI development bundle passed original
Essentia build/linkage, isolated DLL closure/startup, synthetic WAV/FLAC/MP3
Mel parity, EffNet 1280D and 87/56/2 heads, two-worker four-file sidecar
scan, repeat-scan cache reuse and a read-only invocation of the **unchanged**
PR #16 similarity evaluator.

- [Successful run #39421541546](https://github.com/chrober/bliss-mood-poc/actions/runs/39421541546)
  at **`bdb281d3a952775d62f4b29786e687a05471f9b1`**.
- Artifact **`bliss-mood-essentia-windows-x64-dev`**, expires
  2026-11-03; read `README.md` and `BUILD-PROVENANCE.txt`.
- Synthetic parity does **not** establish 100-track real-library parity,
  performance or production redistribution clearance.
- The test kit from that run is still valid for the real-audio test.
  The benchmark Python script belongs to the **new PR #17 checkout**,
  which fixes relative `TracksV2.File` source-root handling and
  verifies backend fingerprint separation. No new native binary is
  required for these Python-only fixes.

## Real-music acceptance criteria

1. Select one existing **bounded 2–500-song** `TracksV2` cohort with
   original exact file keys and accessible music; prefer a representative
   existing `sample-100.db` subset with WAV, FLAC, MP3 and diverse styles.
   **Do not pass the full Bliss database** or a feature sidecar as a cohort.
2. Run Rust and original C++ backends on **exactly the same** audio files,
   executable, model weights, worker count and inference settings.
   Write every run to separate, newly created schema-v3 feature sidecars.
   Keep `bliss.db`, NAS audio, prior 100-track feature DB and all models read-only.
3. No missing/errors; the **exact cohort keys**, requested model-head
   coverage (87D Genre, 56D Mood, 2D Voice), and analyzed Mel patch
   counts must match. **Max absolute per-class score drift <= 1e-3**
   across all pairs. Report per-head mean/max differences and worst
   class/track, not just PASS.
4. Both sides must have **different model fingerprint keys** per head
   (different audio frontends); no single sidecar may mix fingerprints.
   Check that underlying ONNX file hashes, exact class-label order and
   aggregation metadata match **despite** the distinct frontend keys.
   The benchmark asserts all these conditions.
5. Run at 1 and 2 workers first (single and persistent multiworker),
   then extend to 1/2/4/6 and two balanced AB/BA repeats only after
   the numerical gate is green and resource use is acceptable.
6. Preserve both data families under separately named paths, and compare
   per-head similarity distribution, nearest-neighbor ranking overlap and
   zero-score rate **on identical song keys**. Earlier Rust-based Mood/Genre
   findings remain hypotheses, not proof of new C++ model behavior.
7. Merge #17 only after the real-cohort numerical gate, CI, review and
   sidecar isolation pass. The license audit remains a separate
   release/distribution gate; merging experimental code is **not**
   production redistribution approval.

## Windows PowerShell quick compatibility test

Prerequisites: local checkout of the #17 branch, unpacked dev kit
`D:\LMS\essentia-cli-test`, external ONNX weights in
`D:\LMS\bliss-mood-poc\models`, and a **real, bounded** Bliss
`TracksV2` subset (the path below is an example of the existing fixture).
Set `$music` to the actual read-only NAS root. For relative keys, pass
`--source-root` alone. For absolute old paths to be remapped, add
`--library-root <original-prefix>`.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $kit = 'D:\LMS\essentia-cli-test'
    $cohort = Join-Path $repo 'benchmark-workers-20261019-060347\sample-100.db'
    $models = Join-Path $repo 'models'
    $music = '\\192.168.1.100\music'  # Replace with actual source root
    $out = Join-Path $repo 'benchmark-essentia-cpp-real-parity'
    $analyzer = Join-Path $kit 'bliss-mood.exe'
    $worker = Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'

    foreach ($path in @($cohort, $analyzer, $worker)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required file missing: $path"
        }
    }
    foreach ($path in @($models, $music)) {
        if (-not (Test-Path -LiteralPath $path -PathType Container)) {
            throw "Required directory missing: $path"
        }
    }
    if (Test-Path -LiteralPath $out) {
        throw "Choose a NEW output directory, never overwrite: $out"
    }
    Set-Location $repo
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Git switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

    python -m unittest discover -s tests -p 'test_benchmark_audio_backends.py'
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark Python regression tests failed' }

    $args = @(
        'scripts/benchmark_audio_backends.py',
        '--cohort-db', $cohort,
        '--analyzer', $analyzer,
        '--essentia-worker', $worker,
        '--models-dir', $models,
        '--source-root', $music,
        '--output-dir', $out,
        '--models', 'genre,moodtheme,voice',
        '--workers', '1,2',
        '--repeats', '1',
        '--seed', '20261020',
        '--score-max-tolerance', '0.001'
    )
    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Real-music backend parity failed; inspect $out"
    }
    $r = Get-Content -LiteralPath (Join-Path $out 'summary.json') -Raw |
        ConvertFrom-Json
    Write-Host 'Numerical parity by worker count:'
    $r.backend_parity |
        Select-Object workers,tracks_and_heads,compared_scores,
            patch_count_mismatches,maximum_absolute_score_difference,
            mean_absolute_score_difference,fingerprint_heads_checked |
        Format-List
    Write-Host "Validated sidecars, reports, and logs: $out"
}
```

**If this fails:** inspect the error and the run's `*.stderr.txt`.
If scores differ beyond tolerance or patch counts drift, the benchmark
also writes **`parity-failure.json`** with the worst track, class index,
per-head max/mean errors, observed score values and up to ten patch
mismatch examples. Do not change the tolerance to force a pass. A
successful run writes `summary.json` and `runs.csv`. Share only
sanitized diagnostic excerpts; all raw JSON and SQLite files can
contain private music file paths and must stay local.

## Reusing the verified Windows test kit

The original **successful and verified** downloadable artifact is from
run `39421541546`, not an unspecified "latest" run. On Windows with
`gh` authenticated and the repository checkout at
`D:\LMS\bliss-mood-poc`, the package can be downloaded reproducibly:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location 'D:\LMS\bliss-mood-poc'
    $kit = 'D:\LMS\essentia-cli-test'
    if (Test-Path -LiteralPath $kit) {
        throw "Kit directory already exists; inspect instead of overwriting: $kit"
    }
    gh run download 39421541546 `
        --repo chrober/bliss-mood-poc `
        --name bliss-mood-essentia-windows-x64-dev `
        --dir $kit
    if ($LASTEXITCODE -ne 0) { throw 'Kit download failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $kit 'essentia-worker\worker-dependencies.json'))) {
        throw 'Expected signed native dependency manifest not found'
    }
    Write-Host "Package: $kit"
}
```

The `bliss-mood.exe` from this immutable artifact is sufficient for the
next **real-data** run because subsequent PR #17 fixes were confined to
the Python benchmark and accompanying tests/docs. This does **not**
claim that a rebuilt CLI at a newer commit has already passed CI.

## After real-music parity

Only if these results pass, evaluate the **new Essentia sidecar**, for
example `round-01-workers-01-essentia.db`, with PR #16's unchanged
`evaluate_similarity.py` using `--include-experimental`. Keep the
previous Rust sidecar separate and check the exact track key intersection
before comparing metric distributions. This is the next investigation,
not part of the initial compatibility acceptance test.

**Not in scope yet:** production mixing metric selection, subjective
similarity truth, Linux/macOS/Raspberry Pi distribution, licensing audit,
or changing the default `--audio-backend rust`.
