& {
    # NEW independent Bliss-only cohort proposal: no audio/Essentia inference,
    # no Lyrion restart, no network, no training or human labels.
    # Windows PowerShell 5.1 and PowerShell 7; Python 3.15 ONLY.
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $expectedBranch = 'feat/general-pairwise-similarity-research'
    $actual = (& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -cne $expectedBranch) {
        throw 'Expected isolated WP3 research branch; no automatic switch.'
    }
    $python = (Get-Command python -ErrorAction Stop).Source
    $version = @(& $python --version)
    if ($LASTEXITCODE -ne 0 -or ($version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Only the existing Python 3.15 installation is allowed.'
    }
    $script = Join-Path $repo 'scripts/prepare_wp3_independent_cohort.py'
    if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
        throw 'Research cohort source missing. Pull research branch first.'
    }

    # Known user-confirmed source paths, not auto-discovered or invented.
    # Private original 100-song research snapshot MUST be grouped/READY.
    $bliss = Join-Path $repo 'bliss.db'
    $privateBase = Join-Path $repo 'benchmark-wp3-research-20261030-064618-7f8c43a3'
    $identities = Join-Path $privateBase 'lyrion-metadata-eeedcd9630e04da3a3c046db974b33f8'
    $snapshot = Join-Path $identities 'artist-repeat-identities.sqlite'
    $library = Join-Path $identities 'library.db'
    $prior = Join-Path $repo 'benchmark-wp3-research-20261030-091600-8c93d55f/wp3-research.sqlite'

    foreach ($path in @($bliss,$snapshot,$library,$prior)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "A known existing private research SQLite file is not accessible: $path"
        }
    }
    # No calls to SSH, LMS, plugin, audio, or ONNX. No installation.
    $count = 240
    $seed = 20261030
    $runId = [guid]::NewGuid().ToString('N')
    $dest = Join-Path $repo ('benchmark-wp3-independent-cohort-' + $runId)
    if (Test-Path -LiteralPath $dest) {
        throw 'Refuse existing private cohort directory.'
    }

    Write-Host '=== NEW COHORT: READ-ONLY IDENTITY AND AVAILABILITY PREFLIGHT ==='
    $preflight = @($script,
        '--bliss-db',$bliss,
        '--repeat-identity-db',$snapshot,
        '--lyrion-library-db',$library,
        '--prior-research-db',$prior,
        '--count',"$count",'--seed',"$seed",'--preflight')
    & $python @preflight
    if ($LASTEXITCODE -ne 0) {
        throw 'There are not enough new independently identified songs. No files created.'
    }

    Write-Host '=== CREATE EXCLUSIVE PRIVATE MANIFEST (NO AUDIO ANALYSIS) ==='
    New-Item -ItemType Directory -Path $dest -ErrorAction Stop | Out-Null
    $output = Join-Path $dest 'private-independent-cohort.json'
    $args = @($script,
        '--bliss-db',$bliss,
        '--repeat-identity-db',$snapshot,
        '--lyrion-library-db',$library,
        '--prior-research-db',$prior,
        '--count',"$count",'--seed',"$seed",
        '--out-private',$output)
    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw 'Cohort manifest failed; only this new private output may be incomplete.'
    }
    Write-Host '=== NEW PRIVATE COHORT PLAN COMPLETED ==='
    Write-Host "Private planning file (NEVER commit/upload): $output"
    Write-Host 'No new Essentia results exist; no human similarity quality measured.'
    Write-Host 'No audio or ONNX scans; no LMS or player operations.'
}
