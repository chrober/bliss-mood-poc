& {
    # Lyrion WP3: complete, self-contained, read-only local group+teacher study.
    # Windows PowerShell 5.1 or PowerShell 7. Does NOT scan audio or touch PR #16.
    # All four source databases must already be accessible, e.g. mounted shares.
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    $ResearchBranch = 'feat/general-pairwise-similarity-research'
    $SampleLimit = 100
    $Seed = 20261029
    $privateRootBase = if ($env:LOCALAPPDATA) {
        Join-Path $env:LOCALAPPDATA 'LyrionMoodResearch'
    } else {
        Join-Path $env:TEMP 'LyrionMoodResearch'
    }

    function Invoke-Checked {
        param([string]$Executable, [string[]]$Arguments)
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "A required process failed with exit code $LASTEXITCODE"
        }
    }

    function Find-Repo {
        $cursor = (Get-Location).Path
        while ($cursor) {
            if (Test-Path -LiteralPath (Join-Path $cursor '.git')) {
                $remote = (& git -C $cursor remote get-url origin 2>$null)
                if ($LASTEXITCODE -eq 0 -and
                    ($remote -join '') -match '(^|[:/])chrober/bliss-mood-poc(\.git)?$') {
                    return $cursor
                }
            }
            $parent = Split-Path -Parent $cursor
            if (-not $parent -or $parent -eq $cursor) { break }
            $cursor = $parent
        }
        return $null
    }

    function Get-ExactSource {
        param([string]$Variable, [string]$Description)
        $entry = Get-Item -Path ("Env:" + $Variable) -ErrorAction SilentlyContinue
        $candidate = if ($entry) { [string]$entry.Value } else { '' }
        if (-not $candidate) {
            $candidate = Read-Host "$Description (existing exact database path; empty = abort)"
        }
        if (-not $candidate) {
            throw 'Required source was not supplied; no private features have been read.'
        }
        $candidate = $candidate.Trim().Trim('"')
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw 'One required existing source database is not accessible.'
        }
        return (Resolve-Path -LiteralPath $candidate).ProviderPath
    }

    # The source preflight is stdlib-only and works with the local
    # Python 3.15 (also >=3.10). Python 3.13 is ONLY needed later
    # if source provenance, coverage and independent holdout pass.
    foreach ($tool in @('git','python')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Missing required executable: $tool"
        }
    }
    $preflightPython = (Get-Command python -ErrorAction Stop).Source
    $preflightVersion = @(& $preflightPython -c 'import sys; print(int(sys.version_info >= (3,10)))')
    if ($LASTEXITCODE -ne 0 -or ($preflightVersion -join '').Trim() -ne '1') {
        throw 'The source-only Python preflight requires Python 3.10 or newer.'
    }
    Write-Host ('No-write source preflight interpreter: ' +
        ((& $preflightPython --version) -join '').Trim())

    $repoPath = Find-Repo
    if (-not $repoPath) {
        $repoPath = Read-Host 'Path to existing local chrober/bliss-mood-poc clone'
    }
    if (-not $repoPath -or -not (Test-Path -LiteralPath $repoPath -PathType Container)) {
        throw 'A valid local clone is required. No repository has been modified.'
    }
    $repoPath = (Resolve-Path -LiteralPath $repoPath).ProviderPath
    $remote = (& git -C $repoPath remote get-url origin)
    if ($LASTEXITCODE -ne 0 -or ($remote -join '') -notmatch '(^|[:/])chrober/bliss-mood-poc(\.git)?$') {
        throw 'The specified local Git repository is not chrober/bliss-mood-poc.'
    }

    # No recursive audio-library search or filename/path inference.
    $blissDb = Get-ExactSource 'LYRION_BLISS_DB' 'Bliss TracksV2 bliss.db'
    $featuresDb = Get-ExactSource 'LYRION_FEATURE_DB' 'Essentia feature schema-v3 SQLite'
    $snapshotDb = Get-ExactSource 'LYRION_REPEAT_SNAPSHOT_DB' 'BlissMixerLab artist-repeat-identities.sqlite'
    $lyrionDb = Get-ExactSource 'LYRION_LIBRARY_DB' 'Lyrion SQLite library.db'
    $inputPaths = @($blissDb,$featuresDb,$snapshotDb,$lyrionDb)
    if ((@($inputPaths | Select-Object -Unique)).Count -ne 4) {
        throw 'All four source databases must be distinct paths.'
    }

    $before = @{}
    foreach ($sourcePath in $inputPaths) {
        $before[$sourcePath] = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    }

    # Fetch isolated branch only; do not check out or edit PR #16/main.
    $refspec = '+refs/heads/' + $ResearchBranch + ':refs/remotes/origin/' + $ResearchBranch
    Invoke-Checked 'git' @('-C',$repoPath,'fetch','--no-tags','origin',$refspec)
    New-Item -ItemType Directory -Path $privateRootBase -Force | Out-Null
    $nonce = [guid]::NewGuid().ToString('N').Substring(0,12)
    $runRoot = Join-Path $privateRootBase ('wp3-grouped-' + $nonce)
    if (Test-Path -LiteralPath $runRoot) { throw 'Refuse pre-existing output directory.' }
    New-Item -ItemType Directory -Path $runRoot | Out-Null
    $checkout = Join-Path $runRoot 'research-checkout'
    Invoke-Checked 'git' @('-C',$repoPath,'worktree','add','--detach',$checkout,
        ('refs/remotes/origin/' + $ResearchBranch))
    $commit = (& git -C $checkout rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-f]{40}$') {
        throw 'The detached research checkout could not be verified.'
    }

    # Source preflight is stdlib-only: do this BEFORE installing any packages
    # or writing source-derived private output data.
    $groupScript = Join-Path $checkout 'scripts\derive_lyrion_research_groups.py'
    $studyScript = Join-Path $checkout 'scripts\run_local_bliss_essentia_teacher_study.py'
    foreach ($script in @($groupScript,$studyScript)) {
        if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
            throw 'Research scripts are missing from the checked-out commit.'
        }
    }
    $groupFile = Join-Path $runRoot 'private-lyrion-groups.json'
    $reportFile = Join-Path $runRoot 'aggregate-teacher-research.json'

    # The FIRST source pass is a NO-WRITE diagnostic. It provides specific,
    # nonidentifying coverage counts and a fail-closed blocker reason.
    $preflightLines = @(& $preflightPython @($groupScript,
        '--bliss-db',$blissDb,'--feature-db',$featuresDb,
        '--repeat-identity-db',$snapshotDb,'--lyrion-library-db',$lyrionDb,
        '--seed',"$Seed",'--limit',"$SampleLimit",
        '--preflight'))
    if ($LASTEXITCODE -ne 0) {
        throw 'The local read-only source preflight could not validate all four schemas.'
    }
    $preflight = ($preflightLines -join [Environment]::NewLine) | ConvertFrom-Json
    Write-Host ('Source coverage: ' +
        $preflight.counts.paired_tracks_with_verified_lms_artist_album +
        ' paired songs with verified metadata.')
    Write-Host ('Distinct connected artist/album/recording groups: ' +
        $preflight.artist_album_recording_connected_components)
    Write-Host ('Unknown or invalid recording MBIDs: ' +
        $preflight.counts.recording_mbid_unavailable)
    if ($preflight.ready_for_grouped_study -ne $true) {
        Write-Host ('Blocked research reason: ' + $preflight.blocking_reason_code)
        throw 'A reliable artist/album/recording-disjoint holdout is unavailable. No private groups or analysis results were created.'
    }


    # Pinned NumPy/SciPy/scikit-learn versions are verified in CI on
    # Python 3.13. Do not try incompatible wheels on Python 3.15.
    # A parallel 3.13 install changes no default Python installation.
    # Never install any Python runtime without an explicit user action.
    $python313Present = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $python313Probe = @(& py -3.13 -c 'import sys; print(int(sys.version_info[:2] == (3,13)))' 2>&1)
            if ($LASTEXITCODE -eq 0 -and
                ($python313Probe -join '').Trim() -eq '1') {
                $python313Present = $true
            }
        } catch {
            $python313Present = $false
        }
    }
    if (-not $python313Present) {
        Write-Host 'Read-only source preflight PASSED; no private research groups were written.'
        Write-Host 'The numerical stage uses a pinned Python 3.13 environment.'
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
            throw 'Python launcher is unavailable; install Python 3.13 separately before running the numerical stage.'
        }
        # Runtime installation is a separate user-approved side effect.
        # No silent downloading and no changes to the existing Python 3.15.
        $consent = Read-Host 'Install Python 3.13 side-by-side with: py install 3.13 ? [j/N]'
        if ($consent -cnotin @('j','J','ja','JA','y','Y','yes','YES')) {
            throw 'Numerical stage skipped by operator: Python 3.13 not installed.'
        }
        Invoke-Checked 'py' @('install','3.13')
        $installed = @(& py -3.13 -c 'import sys; print(int(sys.version_info[:2] == (3,13)))')
        if ($LASTEXITCODE -ne 0 -or ($installed -join '').Trim() -ne '1') {
            throw 'Python 3.13 installation did not produce a usable runtime.'
        }
        Write-Host 'Separate Python 3.13 runtime is now available for pinned analysis.'
    }

    $venv = Join-Path $runRoot 'venv'
    Invoke-Checked 'py' @('-3.13','-m','venv',$venv)
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw 'Isolated Python environment could not be created.'
    }
    $req = Join-Path $checkout 'research\requirements-wp3-r2.txt'
    Invoke-Checked $venvPython @('-m','pip','install','--no-input','--only-binary=:all:',
        '--disable-pip-version-check','-r',$req)
    Invoke-Checked $venvPython @('-c',
        'import numpy, scipy, sklearn; print("WP3 dependencies:",numpy.__version__,scipy.__version__,sklearn.__version__)')

    Invoke-Checked $venvPython @($groupScript,
        '--bliss-db',$blissDb,'--feature-db',$featuresDb,
        '--repeat-identity-db',$snapshotDb,'--lyrion-library-db',$lyrionDb,
        '--seed',"$Seed",'--limit',"$SampleLimit",
        '--out-groups-private',$groupFile)
    Invoke-Checked $venvPython @($studyScript,
        '--bliss-db',$blissDb,'--feature-db',$featuresDb,
        '--group-metadata-json',$groupFile,
        '--seed',"$Seed",'--limit',"$SampleLimit",
        '--out',$reportFile)

    foreach ($sourcePath in $inputPaths) {
        $afterHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
        if ($afterHash -cne $before[$sourcePath]) {
            throw 'A source database changed during the study; results are invalid.'
        }
    }
    $result = Get-Content -LiteralPath $reportFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($result.status -ne 'EXPLORATORY_DEVELOPMENT_NOT_GENERAL_SIMILARITY_VALIDATION') {
        throw 'Research report has an unexpected status.'
    }
    Write-Host 'Local grouped WP3 research: source files unchanged.'
    Write-Host "Pinned Git research commit: $commit"
    Write-Host ('Number of paired, grouped songs: ' +
        $result.coverage.counts.paired_grouped_songs_accepted)
    Write-Host "Private output directory (do not upload): $runRoot"
    Write-Host ('Aggregate report SHA256: ' +
        (Get-FileHash -LiteralPath $reportFile -Algorithm SHA256).Hash)
    Write-Host 'Teacher reconstruction is NOT independent musical similarity validation.'
}
