# WP1-E3: optional read-only replay of the ALREADY RATED 12-pair local pilot.
# Windows PowerShell 5.1 / PowerShell 7; only private on-disk inputs.
# No new listening, ONNX, audio, SQLite, user queue, or network calls.
# Does NOT select General Metric or claim independent holdout quality.
[CmdletBinding()]
param(
    [string]$Repo = 'D:\LMS\bliss-mood-poc'
)
$ErrorActionPreference = 'Stop'
$Branch = 'feat/general-pairwise-similarity-research'
$Pilot = Join-Path $Repo 'benchmark-local-blinded-ab-pilot12-20261021'
$Ratings = Join-Path $Pilot 'listening-pairs.csv'
$Audit = Join-Path $Pilot 'selection-audit-private.json'
$Evaluator = Join-Path $Repo 'scripts\evaluate_local_listening_pilot.py'
$Venv = Join-Path $Repo 'benchmark-wp3-research-20261030-091600-8c93d55f\venv\Scripts\python.exe'

if (!(Test-Path -LiteralPath $Repo -PathType Container)) {
    throw 'Expected local research repository is missing.'
}
$ActualBranch = (& git -C $Repo branch --show-current)
if ($LASTEXITCODE -ne 0 -or $ActualBranch.Trim() -cne $Branch) {
    throw "Use research branch $Branch and update it before local evaluation."
}
foreach ($Path in @($Ratings, $Audit, $Evaluator)) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw 'Required original private ratings/audit or tracked evaluator missing; no replacement ratings generated.'
    }
}
$Python = if (Test-Path -LiteralPath $Venv -PathType Leaf) {
    $Venv
} else {
    $Cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $Cmd) { throw 'Local Python 3.10+ not found; source ratings remain unmodified.' }
    $Cmd.Source
}
$Out = Join-Path $Repo ('benchmark-wp1-e3-local12-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Out) { throw 'New pilot output must never overwrite existing results.' }

Write-Host '=== WP1-E3: EXISTING 12-PAIR LOCAL HUMAN PILOT (EXPLORATORY) ==='
& $Python $Evaluator '--ratings' $Ratings '--selection-audit' $Audit '--nonmusic-pairs' '10' '--out-dir' $Out
if ($LASTEXITCODE -ne 0) {
    throw 'Existing human ratings and original model audit failed validation; no musical-quality claim made.'
}
$Aggregate = Join-Path $Out 'aggregate-model-comparison.json'
$Private = Join-Path $Out 'numbered-pair-details-private.csv'
if (!(Test-Path -LiteralPath $Aggregate -PathType Leaf) -or
    !(Test-Path -LiteralPath $Private -PathType Leaf)) {
    throw 'Expected locally sealed pilot outputs not found.'
}
Write-Host '=== LOCAL, ORIGINAL-RATING, AGGREGATE-ONLY REPORT READY ==='
Write-Host ('Aggregate (no song keys): ' + $Aggregate)
Write-Host ('Numbered pair diagnostics (PRIVATE; do not publish): ' + $Private)
Write-Host 'Include all 12 pairs AND the original 11-music-only sensitivity (pair 10 excluded only in sensitivity).'
Write-Host 'The 12 deliberately selected pairs are exploratory, not independent confirmation or evidence for production.'
