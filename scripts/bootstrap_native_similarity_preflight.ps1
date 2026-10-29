<#
Automatic, safe and read-only preflight bootstrap. Does not start a native
song scan, overwrite research data, change PR #16 or redistribute native kits.
#>
[CmdletBinding()]
param(
    [string]$Repo = 'D:\LMS\bliss-mood-poc',
    [string]$Worktree = 'D:\LMS\bliss-mood-native-bridge',
    [string]$BinDir = 'D:\LMS\bliss-mood-private\verified-scanner-40758319812',
    [string]$Worker = 'D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe',
    [string]$ModelsDir = 'D:\LMS\bliss-mood-poc\models',
    [string]$AudioRoot = '\\192.168.1.100\music',
    [string]$OutDir = 'D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029'
)

$ErrorActionPreference = 'Stop'
$Branch = 'feat/native-similarity-cohort-validation'
$WorkflowId = 40758319812
$RepoName = 'chrober/bliss-mood-poc'
$SourceSHA = 'da8fecee23930c2e52abcb473a62b8178b2d5474'
$ExeSHA = '00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d'
$OldDb = Join-Path $Repo 'benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db'
$OldEmbeddings = Join-Path $Repo 'benchmark-local-song-embeddings-full100-20261021'

function Require-File([string]$Path, [string]$Role) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing local prerequisite: $Role"
    }
}
function Require-Dir([string]$Path, [string]$Role) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Missing local prerequisite: $Role"
    }
}
function Call-Git([string[]]$Arguments) {
    $output = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git operation failed (exit=$LASTEXITCODE)." }
    return $output
}
function Check-Hash([string]$Path, [string]$Expected) {
    Require-File $Path 'file for SHA256 check'
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected.ToLowerInvariant()) {
        throw 'File SHA256 differs from trusted reference.'
    }
}
function Check-Scanner([string]$Directory) {
    $exe = Join-Path $Directory 'bliss-mood.exe'
    $build = Join-Path $Directory 'BUILD.txt'
    $sums = Join-Path $Directory 'SHA256SUMS.txt'
    Check-Hash $exe $ExeSHA
    Require-File $build 'scanner build provenance'
    Require-File $sums 'scanner SHA256SUMS'
    if (-not (Get-Content -LiteralPath $build -Raw -Encoding UTF8).Contains($SourceSHA)) {
        throw 'Scanner build metadata does not match pinned source.'
    }
    $matches = @(Get-Content -LiteralPath $sums -Encoding UTF8 | Where-Object {
        $_ -match '^\s*[0-9a-fA-F]{64}\s+\*?bliss-mood\.exe\s*$'
    })
    if ($matches.Count -ne 1) {
        throw 'No unique bliss-mood.exe checksum in SHA256SUMS.'
    }
    $recorded = ($matches[0] -split '\s+')[0].ToLowerInvariant()
    if ($recorded -cne $ExeSHA) { throw 'Scanner manifest checksum mismatch.' }
    return $exe
}
function Check-Worker([string]$Executable) {
    Require-File $Executable 'original native Essentia C++ worker EXE'
    $folder = Split-Path -Parent $Executable
    $manifestPath = Join-Path $folder 'worker-dependencies.json'
    Require-File $manifestPath 'native worker-dependencies.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or
        $manifest.platform -cne 'windows-x86_64-mingw64' -or
        $manifest.worker_executable -cne [IO.Path]::GetFileName($Executable).ToLowerInvariant()) {
        throw 'Native worker dependency manifest has unexpected identity.'
    }
    $entries = @($manifest.files.PSObject.Properties)
    if ($entries.Count -lt 2 -or $entries.Count -gt 256) {
        throw 'Invalid number of packaged native executable/DLL dependencies.'
    }
    $names = @($entries | ForEach-Object { $_.Name })
    if ($names -cnotcontains $manifest.worker_executable) {
        throw 'Worker EXE missing from its packaged dependency inventory.'
    }
    $physical = @(Get-ChildItem -LiteralPath $folder -File | Where-Object {
        $_.Extension.ToLowerInvariant() -in @('.exe', '.dll')
    } | ForEach-Object { $_.Name.ToLowerInvariant() })
    if (@(Compare-Object -ReferenceObject ($names | Sort-Object) -DifferenceObject ($physical | Sort-Object)).Count -ne 0) {
        throw 'Packaged native binary directory differs from its dependency manifest.'
    }
    foreach ($item in $entries) {
        $name = $item.Name
        if ($name -cnotmatch '^[a-z0-9_.+-]+\.(exe|dll)$' -or
            $name.Contains('..') -or $item.Value.sha256 -notmatch '^[a-fA-F0-9]{64}$') {
            throw 'Invalid native worker dependency entry.'
        }
        $dependency = Join-Path $folder $name
        Require-File $dependency 'recorded DLL/EXE dependency'
        if ((Get-Item -LiteralPath $dependency).Length -ne [long]$item.Value.size_bytes) {
            throw 'Native dependency size differs from packaged manifest.'
        }
        Check-Hash $dependency ([string]$item.Value.sha256)
    }
    return (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash.ToLowerInvariant()
}

Write-Host ''
Write-Host '=== AUTOMATISCH: REPOSITORY AKTUALISIEREN ===' -ForegroundColor Cyan
Require-Dir $Repo 'original repository'
foreach ($command in @('git', 'gh', 'python')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required CLI missing: $command"
    }
}
& python --version
if ($LASTEXITCODE -ne 0) { throw 'Python could not start.' }
Call-Git @('-C', $Repo, 'fetch', '--no-tags', 'origin', $Branch) | Out-Null
$targetSha = ([string](Call-Git @('-C', $Repo, 'rev-parse', "refs/remotes/origin/$Branch"))).Trim()
if ($targetSha -notmatch '^[a-f0-9]{40}$') { throw 'Invalid fetched bridge SHA.' }
if (-not (Test-Path -LiteralPath $Worktree)) {
    Call-Git @('-C', $Repo, 'worktree', 'add', '--detach', $Worktree, $targetSha) | Out-Null
}
else {
    $inside = ([string](Call-Git @('-C', $Worktree, 'rev-parse', '--is-inside-work-tree'))).Trim()
    if ($inside -cne 'true') { throw 'Existing tool worktree is not a Git checkout.' }
    $dirty = @(Call-Git @('-C', $Worktree, 'status', '--porcelain', '--untracked-files=normal'))
    if ($dirty.Count -gt 0 -and -not ($dirty.Count -eq 1 -and [string]::IsNullOrWhiteSpace($dirty[0]))) {
        throw 'Tool worktree contains local changes; will not overwrite.'
    }
    $head = ([string](Call-Git @('-C', $Worktree, 'rev-parse', 'HEAD'))).Trim()
    if ($head -cne $targetSha) {
        Call-Git @('-C', $Worktree, 'checkout', '--detach', $targetSha) | Out-Null
    }
}
$Bridge = Join-Path $Worktree 'scripts\native_similarity_cohort_bridge.py'
Require-File $Bridge 'current native cohort bridge'
Write-Host "Bridge commit: $targetSha" -ForegroundColor Green

Write-Host ''
Write-Host '=== AUTOMATISCH: VERIFIZIERTES WINDOWS-ARTEFAKT ===' -ForegroundColor Cyan
$run = & gh run view $WorkflowId --repo $RepoName --json headSha,conclusion | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $run.conclusion -cne 'success' -or $run.headSha -cne $SourceSHA) {
    throw 'Trusted GitHub workflow did not match source fingerprint.'
}
if (Test-Path -LiteralPath $BinDir) {
    $Exe = Check-Scanner $BinDir
}
else {
    $parent = Split-Path -Parent $BinDir
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $stage = "$BinDir.download-$PID"
    if (Test-Path -LiteralPath $stage) { throw 'Existing partial scanner staging directory.' }
    New-Item -ItemType Directory -Path $stage | Out-Null
    & gh run download $WorkflowId --repo $RepoName --name bliss-mood-windows-x64 --dir $stage
    if ($LASTEXITCODE -ne 0) { throw 'Scanner download failed. No originals modified.' }
    $discard = Check-Scanner $stage
    Move-Item -LiteralPath $stage -Destination $BinDir
    $Exe = Check-Scanner $BinDir
}
Write-Host 'Scanner provenance and checksum verified.' -ForegroundColor Green

Write-Host ''
Write-Host '=== AUTOMATISCH: LOKALE ABHAENGIGKEITEN ===' -ForegroundColor Cyan
Require-File $OldDb 'frozen Rust-v5 100-song SQLite'
Require-Dir $OldEmbeddings '100 frozen song embedding exports'
Require-Dir $ModelsDir 'official ONNX models and class metadata'
Require-Dir $AudioRoot 'Windows-accessible NAS music root'
$WorkerSha = Check-Worker $Worker
Write-Host 'Original native worker and full DLL closure verified.' -ForegroundColor Green

Write-Host ''
Write-Host '=== AUTOMATISCH: 100-SONG PREFLIGHT (KEIN SCAN) ===' -ForegroundColor Cyan
if (Test-Path -LiteralPath $OutDir) {
    throw 'Preflight output directory already exists. No overwrite permitted.'
}
$arguments = @(
    $Bridge, 'prepare',
    '--baseline-db', $OldDb,
    '--baseline-embeddings', $OldEmbeddings,
    '--audio-root', $AudioRoot,
    '--models-dir', $ModelsDir,
    '--scanner', $Exe,
    '--worker', $Worker,
    '--expected-scanner-sha256', $ExeSHA,
    '--expected-worker-sha256', $WorkerSha,
    '--out-dir', $OutDir
)
& python @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'Preflight failed at the printed diagnostic stage. Native scan NOT started.'
}
Write-Host ''
Write-Host 'PREFLIGHT PASS. No songs analyzed; no original research data modified.' -ForegroundColor Green
