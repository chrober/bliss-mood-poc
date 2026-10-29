& {
    # Build a private WP3 research SQLite from existing local features.
    # PowerShell 5.1 / 7; Python 3.15 only. No new audio/ONNX scans.
    # Does not check out/change main, PR #16 or external repositories.
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest

    function Invoke-Checked {
        param([string]$Executable, [string[]]$Arguments)
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Required process failed with exit code $LASTEXITCODE"
        }
    }

    $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $branch = (& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or
        $branch -cne 'feat/general-pairwise-similarity-research') {
        throw 'Run from the updated feature research branch; no automatic Git switch.'
    }
    $python = (Get-Command python -ErrorAction Stop).Source
    $pythonVersion = @(& $python --version)
    if ($LASTEXITCODE -ne 0 -or
        ($pythonVersion -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Python 3.15 is required. No other Python will be installed or selected.'
    }
    Write-Host ('Research interpreter: ' + ($pythonVersion -join '').Trim())
    if ($env:LYRION_WP3_RUNTIME_SMOKE_ONLY -eq '1') {
        Invoke-Checked $python @('-c',
            'import sys; assert sys.version_info[:2] == (3,15)')
        Write-Host 'WP3 consolidated DB PowerShell 5.1/7 runtime smoke: PASS'
        return
    }

    # Paths are taken from the ACTUAL local research records, not a guessed
    # location or recursive scan. Allow an explicit operator override.
    $bliss = Join-Path $repo 'bliss.db'
    $nativeDefault = Join-Path $repo 'benchmark-native-similarity-100-20261029\native-features.sqlite'
    $native = if ($env:LYRION_FEATURE_DB) {
        $env:LYRION_FEATURE_DB
    } else {
        $nativeDefault
    }
    if (-not (Test-Path -LiteralPath $bliss -PathType Leaf)) {
        throw 'Existing local bliss.db not found. No file has been created.'
    }
    if (-not (Test-Path -LiteralPath $native -PathType Leaf)) {
        throw ('Recorded native Essentia source not found. Check the completed ' +
            '100-song scan; set LYRION_FEATURE_DB to the exact EXISTING file only.')
    }

    $bridge = Join-Path $repo 'scripts\build_wp3_research_db.py'
    $study = Join-Path $repo 'scripts\run_local_bliss_essentia_teacher_study.py'
    $req = Join-Path $repo 'research\requirements-wp3-py315.txt'
    foreach ($required in @($bridge,$study,$req)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw 'Update your existing research branch with git pull --ff-only.'
        }
    }

    # Genuine artist/album/recording provenance may live on the Lyrion host.
    # NEVER infer it from directory names or the song filename.
    $extra = @()
    if ($env:LYRION_REPEAT_SNAPSHOT_DB -and $env:LYRION_LIBRARY_DB) {
        if (-not (Test-Path -LiteralPath $env:LYRION_REPEAT_SNAPSHOT_DB -PathType Leaf) -or
            -not (Test-Path -LiteralPath $env:LYRION_LIBRARY_DB -PathType Leaf)) {
            throw 'One explicitly supplied Lyrion metadata database is inaccessible.'
        }
        $extra = @('--repeat-identity-db',$env:LYRION_REPEAT_SNAPSHOT_DB,
                   '--lyrion-library-db',$env:LYRION_LIBRARY_DB)
    } elseif ($env:LYRION_REPEAT_SNAPSHOT_DB -or $env:LYRION_LIBRARY_DB) {
        throw 'Both exact existing Lyrion metadata SQLite paths must be supplied together.'
    } else {
        Write-Host 'No exact Lyrion metadata sources configured: feature snapshot only.'
        Write-Host 'Training/evaluation requiring independent artist/album/recording groups remains BLOCKED.'
    }

    $seed = 20261029
    $limit = 300
    $inputs = @('--bliss-db',$bliss,'--feature-db',$native,
                '--seed',"$seed",'--limit',"$limit") + $extra

    # First pass: ONLY read sources, print anonymized coverage. No output DB.
    Write-Host '=== WP3 READ-ONLY PREFLIGHT ==='
    $coverageLines = @(& $python $bridge @inputs)
    if ($LASTEXITCODE -ne 0) {
        throw 'WP3 feature source preflight failed. No research DB was created.'
    }
    $coverage = ($coverageLines -join [Environment]::NewLine) | ConvertFrom-Json
    Write-Host ('Exact-key paired Bliss / Essentia tracks: ' +
        $coverage.counts.paired_bliss_essentia_tracks)
    Write-Host ('Group provenance: ' + $coverage.groups.status)
    if ($coverage.counts.paired_bliss_essentia_tracks -lt 1) {
        throw 'No usable paired tracks; cannot create a research snapshot.'
    }

    # Unique, ignored PRIVATE destination. No overwrites of previous runs.
    $id = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' +
          [guid]::NewGuid().ToString('N').Substring(0,8)
    $privateDir = Join-Path $repo ('benchmark-wp3-research-' + $id)
    if (Test-Path -LiteralPath $privateDir) {
        throw 'Refuse existing output directory.'
    }
    $null = New-Item -ItemType Directory -Path $privateDir
    $outDb = Join-Path $privateDir 'wp3-research.sqlite'
    Write-Host '=== NEW PRIVATE WP3 FEATURE SNAPSHOT (NO AUDIO SCAN) ==='
    $buildArgs = @($bridge) + $inputs + @('--out-db',$outDb)
    Invoke-Checked $python $buildArgs

    if ($coverage.groups.status -ne 'READY') {
        Write-Host 'Private research feature DB created successfully.'
        Write-Host 'Lyrion grouping is not yet verified. No teacher training or scientific similarity claim.'
        Write-Host "Private DB (do not upload): $outDb"
        Write-Host 'Next prerequisite is authentic Lyrion artist/album/recording metadata; no manual song labels required.'
        return
    }

    # Only on verified group provenance: fit strictly train-side teacher
    # models in a PRIVATE venv created from this very same Python 3.15.
    Write-Host '=== GROUPED WP3 TEACHER-DEVELOPMENT STUDY ==='
    $venv = Join-Path $privateDir 'venv'
    Invoke-Checked $python @('-m','venv',$venv)
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    Invoke-Checked $venvPython @('-m','pip','install','--no-input',
        '--disable-pip-version-check','--only-binary=:all:','-r',$req)
    $aggregate = Join-Path $privateDir 'aggregate-teacher-research.json'
    Invoke-Checked $venvPython @($study,'--research-db',$outDb,
        '--seed',"$seed",'--out',$aggregate)
    Write-Host 'Grouped teacher development completed (NOT general metric validation).'
    Write-Host "Private research DB (do not upload): $outDb"
    Write-Host "Private aggregate output (no private song identities): $aggregate"
}
