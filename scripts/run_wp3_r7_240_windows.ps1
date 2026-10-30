[CmdletBinding()]
param(
    [string]$PlanDir=''
)
& {
    # Post-R6, read-only teacher-proxy robustness. NO audio, LMS or scanner calls.
    $ErrorActionPreference='Stop'
    Set-StrictMode -Version Latest
    $Repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $Branch=(& git -C $Repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $Branch -cne 'feat/general-pairwise-similarity-research') {
        throw 'WP3 R7 only runs on the isolated similarity research branch.'
    }
    $Python=(Get-Command python -ErrorAction Stop).Source
    $Version=@(& $Python --version)
    if ($LASTEXITCODE -ne 0 -or ($Version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'WP3 R7 requires the existing Python 3.15 installation.'
    }

    $DefaultPlan='benchmark-wp3-r6-native240-f8c65ca449eb40e8ad6b5b3e817c18b2'
    if (-not $PlanDir) { $PlanDir=Join-Path $Repo $DefaultPlan }
    $OldGrouped=Join-Path $Repo 'benchmark-wp3-research-20261030-091600-8c93d55f\wp3-research.sqlite'
    $Bliss=Join-Path $Repo 'bliss.db'
    $R5=Join-Path $Repo 'benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc\private-independent-cohort.json'
    $Protocol=Join-Path $Repo 'research\wp3-r6-full-teacher-evaluation-v1.json'
    $Evaluator=Join-Path $Repo 'scripts\evaluate_wp3_r7_240.py'
    $R6Report=Join-Path $PlanDir 'aggregate-wp3-r6-frozen-teacher-evaluation.json'
    $Venv=Join-Path $Repo 'benchmark-wp3-research-20261030-091600-8c93d55f\venv\Scripts\python.exe'
    foreach ($File in @($OldGrouped,$Bliss,$R5,$Protocol,$Evaluator,$R6Report,$Venv,
                         (Join-Path $PlanDir 'private-scan-plan.json'),
                         (Join-Path $PlanDir 'native-features.sqlite'))) {
        if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
            throw "Required existing private WP3-R7 input missing: $File"
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $PlanDir 'embeddings') -PathType Container)) {
        throw 'Existing R6 embeddings folder missing; do not rescan automatically.'
    }
    $OutputDir=Join-Path $Repo ('benchmark-wp3-r7-posthoc-' + [guid]::NewGuid().ToString('N'))
    if (Test-Path -LiteralPath $OutputDir) { throw 'Fresh output path unexpectedly exists.' }
    $null=New-Item -Path $OutputDir -ItemType Directory -ErrorAction Stop
    $Report=Join-Path $OutputDir 'aggregate-wp3-r7-song-bootstrap-retrieval.json'
    $ArgsList=@(
        $Evaluator,
        '--plan-dir',$PlanDir,
        '--old-grouped-research-db',$OldGrouped,
        '--bliss-db',$Bliss,
        '--r5-manifest',$R5,
        '--frozen-protocol',$Protocol,
        '--r6-report',$R6Report,
        '--out',$Report
    )
    Write-Host '=== WP3-R7: FROZEN R6 PROVENANCE, GROUPED BOOTSTRAP, TOP-K RETRIEVAL ==='
    & $Venv @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw 'WP3-R7 evaluation blocked. Do not interpret incomplete output.'
    }
    if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
        throw 'No complete R7 aggregate output was generated.'
    }
    Write-Host "R7 aggregate report (no song identities): $Report"
    Write-Host 'Private feature/audio/model files stay local; no scan or library modifications.'
}
