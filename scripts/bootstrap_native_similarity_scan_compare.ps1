<#
Single-command continuation AFTER the already successful 29-Oct-2026 preflight.
NEVER calls 'prepare' or bootstrap_native_similarity_preflight.ps1.
Updates only the isolated clean worktree, validates the frozen private plan,
the pinned scanner artifact, the installed full native DLL inventory, models,
baseline vectors and 100 original audio SHA256, then SCAN -> COMPARE.
No originals, PR #16 data, native kit, or private artifacts are published.
#>
[CmdletBinding()]
param(
    [ValidateSet('ScanAndCompare', 'CompareOnly')]
    [string]$Mode = 'ScanAndCompare',
    [string]$Repo = 'D:\LMS\bliss-mood-poc',
    [string]$Worktree = 'D:\LMS\bliss-mood-native-bridge',
    [string]$PlanDir = 'D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029',
    [string]$ReportDir = 'D:\LMS\bliss-mood-poc\benchmark-native-similarity-comparison-20261029',
    [string]$BinDir = 'D:\LMS\bliss-mood-private\verified-scanner-40758319812',
    [string]$Worker = 'D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe',
    [string]$ModelsDir = 'D:\LMS\bliss-mood-poc\models',
    [string]$AudioRoot = '\\192.168.1.100\music',
    [switch]$Synced
)
$ErrorActionPreference = 'Stop'
$Branch = 'feat/native-similarity-cohort-validation'
$RepoName = 'chrober/bliss-mood-poc'
$RunId = 40758319812
$SourceSHA = 'da8fecee23930c2e52abcb473a62b8178b2d5474'
$ExeSHA = '00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d'
$WorkerSHA = 'fd6b172f2db84a614c2db5c80b47670f363fbaafa4e2b9db6f02c3fbd262f3da'
$ManifestSHA = 'f4d359fa1187f4a2626c14b7abe4a34f5d2143ec014c1b9e7f01545cc53e0b77'
$OldDbSHA = 'c8bcf43049bd3c3abeccbb3518969ad357153313928b00f59a248c8566e09865'
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
function Check-Hash([string]$Path, [string]$Expected, [string]$Role) {
    Require-File $Path $Role
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -cne $Expected.ToLowerInvariant()) {
        throw "SHA256 mismatch: $Role (stopping without scanning)"
    }
}
function Invoke-GitChecked([string[]]$Arguments) {
    $output = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git failed (exit=$LASTEXITCODE)" }
    return $output
}
function Check-Scanner([string]$Directory) {
    $exe = Join-Path $Directory 'bliss-mood.exe'
    $build = Join-Path $Directory 'BUILD.txt'
    $sums = Join-Path $Directory 'SHA256SUMS.txt'
    Check-Hash $exe $ExeSHA 'pinned bliss-mood.exe'
    Require-File $build 'scanner BUILD.txt'
    Require-File $sums 'scanner SHA256SUMS.txt'
    if (-not (Get-Content -LiteralPath $build -Raw -Encoding UTF8).Contains($SourceSHA)) {
        throw 'Scanner source provenance differs from qualified CI revision'
    }
    $records = @(Get-Content -LiteralPath $sums -Encoding UTF8 | Where-Object {
        $_ -match '^\s*[0-9a-fA-F]{64}\s+\*?bliss-mood\.exe\s*$'
    })
    if ($records.Count -ne 1 -or
        ($records[0] -split '\s+')[0].ToLowerInvariant() -cne $ExeSHA) {
        throw 'Scanner SHA256SUMS.txt checksum does not match'
    }
    return $exe
}
function Check-NativeClosure([string]$Executable) {
    Check-Hash $Executable $WorkerSHA 'original Essentia C++ native worker'
    $folder = Split-Path -Parent $Executable
    $inventory = Join-Path $folder 'worker-dependencies.json'
    Require-File $inventory 'native DLL closure inventory'
    $manifest = Get-Content -LiteralPath $inventory -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or
        $manifest.platform -cne 'windows-x86_64-mingw64' -or
        $manifest.worker_executable -cne [IO.Path]::GetFileName($Executable).ToLowerInvariant()) {
        throw 'Native dependency inventory identity mismatch'
    }
    $entries = @($manifest.files.PSObject.Properties)
    if ($entries.Count -lt 2 -or $entries.Count -gt 256) {
        throw 'Native inventory file count invalid'
    }
    $names = @($entries | ForEach-Object { $_.Name })
    if ($names -cnotcontains $manifest.worker_executable) {
        throw 'Native inventory does not contain the worker'
    }
    $actualNames = @(Get-ChildItem -LiteralPath $folder -File | Where-Object {
        $_.Extension.ToLowerInvariant() -in @('.exe', '.dll')
    } | ForEach-Object { $_.Name.ToLowerInvariant() })
    if (@(Compare-Object -ReferenceObject ($names | Sort-Object) -DifferenceObject ($actualNames | Sort-Object)).Count -ne 0) {
        throw 'Native binary/DLL closure changed since audit'
    }
    foreach ($entry in $entries) {
        if ($entry.Name -cnotmatch '^[a-z0-9_.+-]+\.(exe|dll)$' -or
            $entry.Name.Contains('..') -or
            [string]$entry.Value.sha256 -notmatch '^[0-9a-fA-F]{64}$') {
            throw 'Unsafe native DLL inventory entry'
        }
        $path = Join-Path $folder $entry.Name
        Require-File $path 'native DLL from inventory'
        if ((Get-Item -LiteralPath $path).Length -ne [long]$entry.Value.size_bytes) {
            throw 'Native DLL size mismatch'
        }
        Check-Hash $path ([string]$entry.Value.sha256) 'native dependency'
    }
}
foreach ($command in @('git', 'gh', 'python')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command unavailable: $command"
    }
}
Require-Dir $Repo 'original Git repository'
Write-Host '=== ISOLATED GIT WORKTREE ===' -ForegroundColor Cyan
if (-not $Synced) {
    Invoke-GitChecked -Arguments @('-C', $Repo, 'fetch', '--no-tags', 'origin', $Branch) | Out-Null
    $sha = ([string](Invoke-GitChecked -Arguments @('-C', $Repo, 'rev-parse', "refs/remotes/origin/$Branch"))).Trim()
    if ($sha -notmatch '^[0-9a-f]{40}$') { throw 'Invalid remote bridge commit SHA' }
    if (-not (Test-Path -LiteralPath $Worktree)) {
        Invoke-GitChecked -Arguments @('-C', $Repo, 'worktree', 'add', '--detach', $Worktree, $sha) | Out-Null
    }
}
Require-Dir $Worktree 'isolated bridge Git worktree'
$root = ([string](Invoke-GitChecked -Arguments @('-C', $Worktree, 'rev-parse', '--show-toplevel'))).Trim()
if ([IO.Path]::GetFullPath($root).TrimEnd('\') -ine
    [IO.Path]::GetFullPath($Worktree).TrimEnd('\')) {
    throw 'Bridge worktree does not match expected isolated path'
}
$dirty = @(Invoke-GitChecked -Arguments @('-C', $Worktree, 'status', '--porcelain', '--untracked-files=normal') |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($dirty.Count -gt 0) { throw 'Isolated worktree has changes; refusing checkout' }
if (-not $Synced) {
    $head = ([string](Invoke-GitChecked -Arguments @('-C', $Worktree, 'rev-parse', 'HEAD'))).Trim()
    if ($head -cne $sha) {
        Invoke-GitChecked -Arguments @('-C', $Worktree, 'checkout', '--detach', $sha) | Out-Null
        # Re-enter the UPDATED script rather than executing stale in-memory code.
        & (Join-Path $Worktree 'scripts\bootstrap_native_similarity_scan_compare.ps1') -Mode $Mode -Repo $Repo -Worktree $Worktree -PlanDir $PlanDir -ReportDir $ReportDir -BinDir $BinDir -Worker $Worker -ModelsDir $ModelsDir -AudioRoot $AudioRoot -Synced
        return
    }
}
$head = ([string](Invoke-GitChecked -Arguments @('-C', $Worktree, 'rev-parse', 'HEAD'))).Trim()
Write-Host "Bridge source commit: $head" -ForegroundColor Green

Write-Host '=== PINNED SCANNER AND PRIVATE NATIVE WORKER ===' -ForegroundColor Cyan
$run = & gh run view $RunId --repo $RepoName --json headSha,conclusion | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $run.conclusion -cne 'success' -or $run.headSha -cne $SourceSHA) {
    throw 'Pinned GitHub Actions scanner source/workflow identity failed'
}
if (Test-Path -LiteralPath $BinDir) {
    $Scanner = Check-Scanner $BinDir
} else {
    $parent = Split-Path -Parent $BinDir
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    $stage = "$BinDir.download-$PID"
    if (Test-Path -LiteralPath $stage) { throw 'Scanner staging directory already exists' }
    New-Item -ItemType Directory -Path $stage | Out-Null
    & gh run download $RunId --repo $RepoName --name bliss-mood-windows-x64 --dir $stage
    if ($LASTEXITCODE -ne 0) { throw 'Trusted scanner download failed' }
    $null = Check-Scanner $stage
    Move-Item -LiteralPath $stage -Destination $BinDir
    $Scanner = Check-Scanner $BinDir
}
Check-NativeClosure $Worker
Write-Host 'Scanner, source workflow, worker and entire recorded DLL closure verified.' -ForegroundColor Green

Write-Host '=== FROZEN INPUTS (NO NEW PREPARE) ===' -ForegroundColor Cyan
Require-Dir $PlanDir 'existing successful 100-song preflight plan'
Require-Dir $AudioRoot 'original NAS music root'
Require-Dir $ModelsDir 'official model directory'
Require-Dir $OldEmbeddings 'original 100 song embeddings'
Check-Hash $OldDb $OldDbSHA 'old Rust-v5 SQLite'
$manifest = Join-Path $PlanDir 'exact-100-tracks.txt'
Check-Hash $manifest $ManifestSHA 'frozen 100-song manifest'
$provenance = Join-Path $PlanDir 'provenance.json'
Require-File $provenance 'original preflight provenance'
$plan = Get-Content -LiteralPath $provenance -Raw -Encoding UTF8 | ConvertFrom-Json
if ($plan.schema -cne 'native_similarity_cohort_bridge_v1' -or
    $plan.status -cne 'PREFLIGHT_VERIFIED_NO_NATIVE_SCAN_YET' -or
    $plan.tracks -ne 100 -or
    $plan.source_manifest_sha256 -cne $ManifestSHA -or
    $plan.old_sqlite_sha256 -cne $OldDbSHA -or
    $plan.verified_scanner_exe_sha256 -cne $ExeSHA -or
    $plan.native_worker_exe_sha256 -cne $WorkerSHA) {
    throw 'Existing preflight provenance no longer matches the frozen verified plan'
}
foreach ($entry in $plan.model_file_sha256.PSObject.Properties) {
    Check-Hash (Join-Path $ModelsDir $entry.Name) ([string]$entry.Value) 'original model/metadata'
}
$Verifier = Join-Path $Worktree 'scripts\verify_native_similarity_frozen_inputs.py'
Require-File $Verifier 'read-only frozen-input validator'
& python $Verifier --plan-dir $PlanDir --baseline-db $OldDb --baseline-embeddings $OldEmbeddings --models-dir $ModelsDir --audio-root $AudioRoot
if ($LASTEXITCODE -ne 0) { throw 'Frozen inputs have changed; native scan NOT started' }
Write-Host 'The already frozen 100 identities and source bytes still match.' -ForegroundColor Green

$Runner = Join-Path $Worktree 'scripts\run_native_similarity_cohort.ps1'
Require-File $Runner 'existing scan/compare runner'
$NativeDb = Join-Path $PlanDir 'native-features.sqlite'
$NativeDir = Join-Path $PlanDir 'native-embeddings'
Require-Dir $NativeDir 'existing empty/native embedding destination'
if (Test-Path -LiteralPath $ReportDir) {
    throw 'Existing comparison directory must not be overwritten'
}
if ($Mode -eq 'ScanAndCompare') {
    Write-Host '=== NATIVE 100-SONG SCAN (STATIC --workers auto, --threads 1) ===' -ForegroundColor Cyan
    foreach ($item in @($NativeDb, "$NativeDb-wal", "$NativeDb-shm", "$NativeDb-journal")) {
        if (Test-Path -LiteralPath $item) {
            throw 'Native SQLite or journal already exists; no blind retry. Use CompareOnly only after checking scan completeness.'
        }
    }
    if (@(Get-ChildItem -LiteralPath $NativeDir -Force).Count -gt 0) {
        throw 'Native embeddings target is not empty; refusing to overwrite or retry'
    }
    & $Runner -Step scan -OldRepo $Repo -AudioRoot $AudioRoot -ModelsDir $ModelsDir -ScannerExe $Scanner -NativeWorker $Worker -PlanDir $PlanDir -ReportDir $ReportDir
    if (-not $?) { throw 'Native scan failed; no comparison was started' }
} else {
    Require-File $NativeDb 'completed native SQLite for CompareOnly'
    Write-Host 'CompareOnly: existing native output is preserved; scanner not invoked.' -ForegroundColor Yellow
}
Write-Host '=== FULL 4,950-PAIR AND 12/11 HUMAN PILOT COMPARISON ===' -ForegroundColor Cyan
& $Runner -Step compare -OldRepo $Repo -ModelsDir $ModelsDir -ScannerExe $Scanner -NativeWorker $Worker -PlanDir $PlanDir -ReportDir $ReportDir
if (-not $?) { throw 'Comparison failed; preserve outputs for diagnosis' }
$report = Join-Path $ReportDir 'aggregate-native-cohort-comparison.json'
Require-File $report 'anonymous aggregate comparison report'
$result = Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
if ($result.complete_song_pairs -ne 4950 -or $result.track_count -ne 100) {
    throw 'Unexpected comparison population; do not interpret report'
}
Write-Host "Comparison status: $($result.status)" -ForegroundColor Green
Write-Host "Anonymized aggregate report: $report" -ForegroundColor Green
Write-Host 'PRIVATE aggregate report created. Diagnostic backend comparison only; no general similarity winner is asserted.' -ForegroundColor Green
