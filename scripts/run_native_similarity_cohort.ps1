<#
Three safe local stages: prepare, scan, compare.
The existing Rust-v5 feature DB, human ratings, audio and sidecars are read-only.
The only output targets are new private benchmark-native-* directories.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('prepare', 'scan', 'compare')]
    [string]$Step,
    [string]$OldRepo = 'D:\LMS\bliss-mood-poc',
    [string]$AudioRoot,
    [string]$ModelsDir,
    [string]$ScannerExe,
    [string]$NativeWorker,
    [string]$PlanDir,
    [string]$ReportDir
)

$ErrorActionPreference = 'Stop'
$ExpectedScanner = '00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d'
$Bridge = Join-Path $PSScriptRoot 'native_similarity_cohort_bridge.py'
$OldDb = Join-Path $OldRepo 'benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db'
$OldEmbeddings = Join-Path $OldRepo 'benchmark-local-song-embeddings-full100-20261021'
$Pilot = Join-Path $OldRepo 'benchmark-local-blinded-ab-pilot12-20261021'
$Ratings = Join-Path $Pilot 'listening-pairs.csv'
$SealedAudit = Join-Path $Pilot 'selection-audit-private.json'

if (-not $PlanDir) {
    $PlanDir = Join-Path $OldRepo 'benchmark-native-similarity-100-20261029'
}
if (-not $ReportDir) {
    $ReportDir = Join-Path $OldRepo 'benchmark-native-similarity-comparison-20261029'
}
function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required private file is unavailable: $Path"
    }
}
function Assert-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Required private directory is unavailable: $Path"
    }
}
function Assert-Hash([string]$Path, [string]$Expected) {
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -cne $Expected.ToLowerInvariant()) {
        throw "File SHA256 changed since verified preflight: $Path"
    }
}
function Assert-PlanHashes([object]$Plan) {
    Assert-File $ScannerExe
    Assert-File $NativeWorker
    Assert-Directory $ModelsDir
    Assert-Hash $ScannerExe ([string]$Plan.verified_scanner_exe_sha256)
    Assert-Hash $NativeWorker ([string]$Plan.native_worker_exe_sha256)
    foreach ($File in $Plan.model_file_sha256.PSObject.Properties) {
        Assert-Hash (Join-Path $ModelsDir $File.Name) ([string]$File.Value)
    }
    Assert-Hash (Join-Path $PlanDir 'exact-100-tracks.txt') ([string]$Plan.source_manifest_sha256)
}
Assert-File $Bridge

if ($Step -eq 'prepare') {
    Assert-File $OldDb
    Assert-Directory $OldEmbeddings
    Assert-Directory $AudioRoot
    Assert-Directory $ModelsDir
    Assert-File $ScannerExe
    Assert-File $NativeWorker
    if (Test-Path -LiteralPath $PlanDir) {
        throw "Do not overwrite existing preflight: $PlanDir"
    }
    Assert-Hash $ScannerExe $ExpectedScanner

    $Arguments = @(
        $Bridge, 'prepare',
        '--baseline-db', $OldDb,
        '--baseline-embeddings', $OldEmbeddings,
        '--audio-root', $AudioRoot,
        '--models-dir', $ModelsDir,
        '--scanner', $ScannerExe,
        '--worker', $NativeWorker,
        '--expected-scanner-sha256', $ExpectedScanner,
        '--out-dir', $PlanDir
    )
    & python @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; native scan is NOT authorized.' }
    Write-Host 'Preflight PASS: exactly 100 frozen track keys and source hashes.'
}
elseif ($Step -eq 'scan') {
    Assert-Directory $PlanDir
    Assert-Directory $AudioRoot
    $ProvenancePath = Join-Path $PlanDir 'provenance.json'
    Assert-File $ProvenancePath
    $Plan = Get-Content -LiteralPath $ProvenancePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Plan.schema -cne 'native_similarity_cohort_bridge_v1' -or $Plan.tracks -ne 100) {
        throw 'Invalid preflight manifest/provenance contract.'
    }
    Assert-PlanHashes $Plan

    $NativeDb = Join-Path $PlanDir 'native-features.sqlite'
    $NativeEmbeddings = Join-Path $PlanDir 'native-embeddings'
    Assert-Directory $NativeEmbeddings
    if (Test-Path -LiteralPath $NativeDb -PathType Leaf) {
        throw 'Native DB exists. Inspect any partial run before retrying.'
    }
    $Arguments = @(
        'scan-features',
        '--tracks-file', (Join-Path $PlanDir 'exact-100-tracks.txt'),
        '--source-root', $AudioRoot,
        '--db', $NativeDb,
        '--embedding-dir', $NativeEmbeddings,
        '--models-dir', $ModelsDir,
        '--models', 'moodtheme,genre,voice',
        '--audio-backend', 'essentia',
        '--essentia-worker', $NativeWorker,
        '--workers', 'auto',
        '--threads', '1',
        '--max-errors', '3',
        '--json'
    )
    & $ScannerExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Native scan stopped; do NOT blindly retry on partially written outputs.'
    }
    Write-Host 'Scanner returned success. Run the separate compare gate.'
}
elseif ($Step -eq 'compare') {
    Assert-Directory $PlanDir
    Assert-File $OldDb
    Assert-Directory $OldEmbeddings
    Assert-Directory $ModelsDir
    Assert-File $Ratings
    Assert-File $SealedAudit

    $ProvenancePath = Join-Path $PlanDir 'provenance.json'
    Assert-File $ProvenancePath
    $Plan = Get-Content -LiteralPath $ProvenancePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-PlanHashes $Plan

    $NativeDb = Join-Path $PlanDir 'native-features.sqlite'
    $NativeEmbeddings = Join-Path $PlanDir 'native-embeddings'
    Assert-File $NativeDb
    Assert-Directory $NativeEmbeddings

    if (Test-Path -LiteralPath $ReportDir) {
        throw "Existing comparison must not be overwritten: $ReportDir"
    }

    $Arguments = @(
        $Bridge, 'compare',
        '--plan-dir', $PlanDir,
        '--baseline-db', $OldDb,
        '--baseline-embeddings', $OldEmbeddings,
        '--native-db', $NativeDb,
        '--native-embeddings', $NativeEmbeddings,
        '--models-dir', $ModelsDir,
        '--native-frontend', 'experimental-essentia-cpp-dsp-v1-unvalidated',
        '--ratings', $Ratings,
        '--pilot-audit', $SealedAudit,
        '--score-tolerance', '0.001',
        '--embedding-cosine-min', '0.999',
        '--out-dir', $ReportDir
    )
    & python @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Comparison failed; preserve private sidecars.' }
    Write-Host 'Comparison complete. Aggregate JSON in private report directory.'
}
