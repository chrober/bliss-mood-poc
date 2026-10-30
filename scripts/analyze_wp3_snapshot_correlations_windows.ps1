& {
    # WP3 local descriptive Bliss/Essentia associations on ONE existing
    # consolidated research SQLite. No audio analysis, no model fitting,
    # no Lyrion connection, no source modification. PS 5.1 / PS 7.
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $active = (& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or
        $active -cne 'feat/general-pairwise-similarity-research') {
        throw 'The existing local clone must be on the research branch.'
    }
    $python = (Get-Command python -ErrorAction Stop).Source
    $version = @(& $python --version)
    if ($LASTEXITCODE -ne 0 -or ($version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Existing Python 3.15 required. No other Python is installed.'
    }

    # Operator overrides this ONLY with a known exact existing DB.
    # Otherwise accept one unique previous private WP3 build, not
    # arbitrarily select the latest among multiple research snapshots.
    $sourceDb = [string]$env:LYRION_WP3_RESEARCH_DB
    if (-not $sourceDb) {
        $candidates = @(
            Get-ChildItem -LiteralPath $repo -Directory -Filter 'benchmark-wp3-research-*' |
                ForEach-Object {
                    Join-Path $_.FullName 'wp3-research.sqlite'
                } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
        )
        if ($candidates.Count -ne 1) {
            throw ('Expected exactly one existing WP3 private research SQLite. ' +
                'If there are several, set LYRION_WP3_RESEARCH_DB explicitly to the desired file.')
        }
        $sourceDb = $candidates[0]
    }
    if (-not (Test-Path -LiteralPath $sourceDb -PathType Leaf)) {
        throw 'The selected WP3 research SQLite is missing; no output created.'
    }
    $sourceDb = (Resolve-Path -LiteralPath $sourceDb).ProviderPath
    $analysis = Join-Path $repo 'scripts\analyze_wp3_snapshot_correlations.py'
    if (-not (Test-Path -LiteralPath $analysis -PathType Leaf)) {
        throw 'Update the research branch with git pull --ff-only first.'
    }

    $outputFolder = Split-Path -Parent $sourceDb
    $name = 'aggregate-wp3-descriptive-' + (Get-Date -Format 'yyyyMMdd-HHmmss') +
            '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.json'
    $report = Join-Path $outputFolder $name
    Write-Host '=== BLISS 23D <-> ESSENTIA 87D + 56D DESCRIPTIVE CORRELATIONS ==='
    Write-Host 'Group-free exploratory associations only; no supervised learning or metric winner.'
    & $python $analysis --research-db $sourceDb --out $report
    if ($LASTEXITCODE -ne 0) {
        throw 'Descriptive WP3 analysis failed; no source database was modified.'
    }
    Write-Host "Private aggregate report (do not commit): $report"
    Write-Host 'Interpretation requires selection-bias cautions and independent music-quality evaluation.'
}
