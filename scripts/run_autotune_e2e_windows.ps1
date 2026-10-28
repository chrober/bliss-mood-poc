# PR #19 - privater, echt gemessener Autotune-End-to-End-Vergleich.
# Standard: ausschliesslich Preflight/Plan; -Execute startet echte Musikscans.
# Keine privaten Ausgaben in git/CI hochladen.
param(
    [switch]$Execute,
    [string]$Repo = 'D:\LMS\bliss-mood-poc',
    [string]$CohortDb = '',
    [string]$SourceRoot = '\\192.168.1.100\music',
    [string]$NativeWorker = 'D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe',
    [string]$ModelsDir = '',
    [string]$LibraryRoot = '',
    [string]$FixedWorkers = '6,8,10,12',
    [int]$InitialWorkers = 6,
    [int]$MinWorkers = 6,
    [int]$MaxWorkers = 12,
    [int]$ExpectedTracks = 100,
    [int]$Repeats = 2
)

& {
    $ErrorActionPreference = 'Stop'
    $repository = 'chrober/bliss-mood-poc'
    $codeSha = '32cba98c229bbfbbeb329badb84212446c3b3721'
    $windowsRun = 40697871147
    if (-not $CohortDb) {
        $CohortDb = Join-Path $Repo 'benchmark-workers-20261019-060347\sample-100.db'
    }
    if (-not $ModelsDir) { $ModelsDir = Join-Path $Repo 'models' }
    $results = Join-Path $Repo ('benchmark-autotune-e2e-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $artifactDir = Join-Path $env:LOCALAPPDATA ('Lyrion\autotune-pr19-' + $codeSha.Substring(0, 8))

    if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
        throw "Repository fehlt: $Repo"
    }
    Set-Location -LiteralPath $Repo
    Write-Host '=== PR #19 UND VERIFIZIERTEN CODE PRUEFEN ==='
    if ((git branch --show-current).Trim() -ne 'feat/ram-safe-online-autotune') {
        throw 'Bitte zuerst zu Branch feat/ram-safe-online-autotune wechseln'
    }
    git cat-file -e "$codeSha^{commit}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Commit zum Binary fehlt lokal: git fetch origin'
    }
    git merge-base --is-ancestor $codeSha HEAD
    if ($LASTEXITCODE -ne 0) {
        throw 'Checkout ist zu alt: git pull --ff-only'
    }
    $sourcePaths = @(
        'src/autotune.rs', 'src/features.rs', 'src/main.rs',
        'scripts/benchmark_native_adaptive_manifest.py',
        'scripts/benchmark_audio_backends.py',
        'scripts/verify_manifest_batch_smoke.py'
    )
    git diff --quiet $codeSha HEAD -- @sourcePaths
    if ($LASTEXITCODE -ne 0) {
        throw 'Scanner-/Benchmark-Code ist neuer als das verifizierte CI-Binary'
    }
    if (@(git status --porcelain --untracked-files=no -- @sourcePaths).Count -ne 0) {
        throw 'Lokale Aenderungen an Scanner-/Benchmark-Code: zuerst sichern'
    }

    Write-Host '=== VORAUSSETZUNGEN PRUEFEN ==='
    foreach ($file in @(
        $CohortDb, $NativeWorker,
        (Join-Path $Repo 'scripts\benchmark_native_adaptive_manifest.py')
    )) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Datei fehlt: $file"
        }
    }
    foreach ($folder in @($SourceRoot, $ModelsDir)) {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
            throw "Verzeichnis fehlt oder ist nicht erreichbar: $folder"
        }
    }
    foreach ($program in @('gh', 'py', 'ffmpeg', 'ffprobe')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
            throw "Programm fehlt im PATH: $program"
        }
    }
    foreach ($model in @(
        'discogs-effnet-bsdynamic-1.onnx',
        'mtg_jamendo_genre-discogs-effnet-1.onnx',
        'mtg_jamendo_moodtheme-discogs-effnet-1.onnx',
        'voice_instrumental-discogs-effnet-1.onnx',
        'mtg_jamendo_genre-discogs-effnet-1.json',
        'mtg_jamendo_moodtheme-discogs-effnet-1.json',
        'voice_instrumental-discogs-effnet-1.json'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $ModelsDir $model) -PathType Leaf)) {
            throw "Offizielle ONNX/JSON-Datei fehlt: $model"
        }
    }
    if (Test-Path -LiteralPath $results) {
        throw "Resultat-Ordner existiert bereits: $results"
    }

    Write-Host '=== WINDOWS-CI-ARTEFAKT UND SHA256 PRUEFEN ==='
    $run = & gh run view $windowsRun --repo $repository --json headSha,conclusion | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $run.conclusion -ne 'success' -or
        $run.headSha -ne $codeSha) {
        throw 'Falsche Source-SHA oder fehlgeschlagener Windows-GitHub-Run'
    }
    if (-not (Test-Path -LiteralPath $artifactDir -PathType Container)) {
        New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
        & gh run download $windowsRun --repo $repository --name 'bliss-mood-windows-x64' --dir $artifactDir
        if ($LASTEXITCODE -ne 0) {
            throw 'CI-Artefakt nicht downloadbar (ggf. abgelaufen)'
        }
    }
    $analyzer = Join-Path $artifactDir 'bliss-mood.exe'
    $build = Join-Path $artifactDir 'BUILD.txt'
    $hashFile = Join-Path $artifactDir 'SHA256SUMS.txt'
    foreach ($file in @($analyzer, $build, $hashFile)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Unvollstaendiges CI-Artefakt: $file"
        }
    }
    $buildText = Get-Content -LiteralPath $build -Raw
    if ($buildText -notmatch "(?m)^Commit:[ \t]*$codeSha\r?$" -or
        $buildText -notmatch "(?m)^Source PR head commit:[ \t]*$codeSha\r?$") {
        throw 'BUILD.txt weist nicht die erwartete Source-SHA nach'
    }
    $hashLines = @(Get-Content -LiteralPath $hashFile |
        Where-Object { $_ -match '^[0-9a-fA-F]{64}\s+\*?bliss-mood\.exe\s*$' })
    if ($hashLines.Count -ne 1) {
        throw 'SHA256SUMS.txt enthaelt keine eindeutige EXE-Pruefsumme'
    }
    $expectedHash = ($hashLines[0] -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath $analyzer -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) {
        throw 'SHA256-Mismatch: CI-Binary nicht verwenden'
    }
    Write-Host "Source-SHA: $codeSha"
    Write-Host "Binary-SHA256: $actualHash"

    Write-Host '=== BALANCIERTER ECHTMUSIK-BENCHMARK ==='
    $pythonArgs = @(
        'scripts/benchmark_native_adaptive_manifest.py',
        '--experiment', 'autotune-e2e',
        '--cohort-db', $CohortDb, '--expected-tracks', [string]$ExpectedTracks,
        '--source-root', $SourceRoot,
        '--analyzer', $analyzer, '--essentia-worker', $NativeWorker,
        '--models-dir', $ModelsDir, '--models', 'moodtheme,genre,voice',
        '--output-dir', $results,
        '--fixed-workers', $FixedWorkers,
        '--autotune-min', [string]$MinWorkers,
        '--autotune-initial', [string]$InitialWorkers,
        '--autotune-max', [string]$MaxWorkers,
        '--scan-priority', 'normal', '--repeats', [string]$Repeats,
        '--seed', '20261028',
        '--min-available-ram-mib', '1536', '--max-system-ram-percent', '90'
    )
    # Nur fuer absolute TracksV2.File-Pfade: Ursprungsroot separat angeben.
    if ($LibraryRoot) { $pythonArgs += @('--library-root', $LibraryRoot) }
    if (-not $Execute) { $pythonArgs += '--plan-only' }
    & py -3 @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Benchmark bzw. Preflight fehlgeschlagen: $results"
    }
    if (-not $Execute) {
        Write-Host '=== PLAN OK: fuer echte Scans denselben Aufruf mit -Execute starten ==='
        return
    }

    Write-Host '=== ENDE-ZU-ENDE-LAUFZEITEN ==='
    $reportPath = Join-Path $results 'summary.json'
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
        throw 'summary.json fehlt'
    }
    $result = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    $expectedRuns = ($FixedWorkers.Split(',').Count + 1) * $Repeats
    if ($result.experiment.experiment -ne 'autotune-e2e' -or
        $result.exact_numeric_parity -ne $true -or
        @($result.runs).Count -ne $expectedRuns) {
        throw 'Benchmark unvollstaendig oder numerische Paritaet fehlgeschlagen'
    }
    $result.aggregates | Sort-Object median_wall_seconds |
        Select-Object mode, repeats, median_wall_seconds,
            median_songs_per_minute, peak_process_tree_private_mib |
        Format-Table -AutoSize
    Write-Host '=== AUTOTUNE GEGEN FESTE WORKER: GEPAARTE MESSRUNDE ==='
    $result.paired_autotune_e2e |
        Select-Object baseline, median_autotune_speedup_percent,
            rounds_autotune_faster, repeats | Format-Table -AutoSize
    Write-Host '=== AUTOTUNE-SUCHDIAGNOSTIK ==='
    $result.runs | Where-Object { $_.mode -eq 'autotune' } |
        Select-Object round, wall_seconds, autotune_probes,
            autotune_search_completed, autotune_best_tested_workers,
            autotune_exploration_budget_holds | Format-Table -AutoSize
    Write-Host '=== FERTIG: PRIVATEN OUTPUT NICHT COMMITTEN ==='
    Write-Host "JSON: $reportPath"
    Write-Host "CSV: $(Join-Path $results 'runs.csv')"
}
