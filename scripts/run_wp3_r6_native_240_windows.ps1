[CmdletBinding()]
param(
    [ValidateSet('Prepare','Scan','Verify','All')]
    [string]$Stage='Prepare',
    [string]$PlanDir=''
)
& {
    # Windows PowerShell 5.1 or 7; original native Essentia C++ pipeline.
    # Stage Prepare is default and has NO inference. Stage All explicitly
    # runs 240-song audio scan; NEVER touches original Bliss/music/old DBs.
    $ErrorActionPreference='Stop'
    Set-StrictMode -Version Latest
    $Repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $Branch=(& git -C $Repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $Branch -cne 'feat/general-pairwise-similarity-research') {
        throw 'WP3 R6 only runs from the isolated similarity research branch.'
    }
    $Python=(Get-Command python -ErrorAction Stop).Source
    $Version=@(& $Python --version)
    if ($LASTEXITCODE -ne 0 -or ($Version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Existing Python 3.15 is mandatory; no fallback/installation.'
    }

    # Previously verified local Windows paths from native 100-song handback.
    # Do not auto-download, share, modify, or distribute native DLLs/EXEs.
    $SourceRoot='\\192.168.1.100\music'
    $Scanner='D:\LMS\bliss-mood-private\verified-scanner-40758319812\bliss-mood.exe'
    $Worker='D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe'
    $Models=Join-Path $Repo 'models'
    $OldMetadata=Join-Path $Repo 'benchmark-wp3-research-20261030-064618-7f8c43a3\lyrion-metadata-eeedcd9630e04da3a3c046db974b33f8'
    $Bliss=Join-Path $Repo 'bliss.db'
    $Snapshot=Join-Path $OldMetadata 'artist-repeat-identities.sqlite'
    $Library=Join-Path $OldMetadata 'library.db'
    $OldGrouped=Join-Path $Repo 'benchmark-wp3-research-20261030-091600-8c93d55f\wp3-research.sqlite'
    $OldNative=Join-Path $Repo 'benchmark-native-similarity-100-20261029\native-features.sqlite'
    $R5=Join-Path $Repo 'benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc\private-independent-cohort.json'
    $Adapter=Join-Path $Repo 'scripts\wp3_r6_native_240.py'
    $Eval=Join-Path $Repo 'scripts\evaluate_wp3_r6_240.py'
    $Frozen=Join-Path $Repo 'research\wp3-r6-full-teacher-evaluation-v1.json'
    $Venv=Join-Path $Repo 'benchmark-wp3-research-20261030-091600-8c93d55f\venv\Scripts\python.exe'

    foreach ($F in @($Scanner,$Worker,$Bliss,$Snapshot,$Library,$OldGrouped,
                      $OldNative,$R5,$Adapter,$Frozen,$Eval,$Venv)) {
        if (-not (Test-Path -LiteralPath $F -PathType Leaf)) {
            throw "Missing existing R6 prerequisite: $F"
        }
    }
    foreach ($D in @($SourceRoot,$Models)) {
        if (-not (Test-Path -LiteralPath $D -PathType Container)) {
            throw "Original local source/model directory missing: $D"
        }
    }
    if ($Stage -eq 'Prepare' -or $Stage -eq 'All') {
        if ($PlanDir) { throw 'Do not specify existing PlanDir for a fresh R6 preparation.' }
        $PlanDir=Join-Path $Repo ('benchmark-wp3-r6-native240-' + [guid]::NewGuid().ToString('N'))
    } elseif (-not $PlanDir) {
        throw 'For Scan/Verify supply the exact existing private -PlanDir from Prepare.'
    }
    $Arguments=@(
        '--bliss-db',$Bliss,
        '--snapshot',$Snapshot,
        '--library',$Library,
        '--old-grouped-db',$OldGrouped,
        '--old-native-db',$OldNative,
        '--r5-manifest',$R5,
        '--source-root',$SourceRoot,
        '--models-dir',$Models,
        '--scanner',$Scanner,
        '--worker',$Worker
    )

    if ($Stage -eq 'Prepare' -or $Stage -eq 'All') {
        Write-Host '=== WP3-R6: FROZEN 240 SOURCE / MODEL / NATIVE PREFLIGHT ==='
        & $Python $Adapter prepare @Arguments --out-dir $PlanDir
        if ($LASTEXITCODE -ne 0) { throw 'R6 source preflight failed; no audio scan.' }
        Write-Host "Private R6 plan: $PlanDir"
    }
    if ($Stage -eq 'Scan' -or $Stage -eq 'All') {
        if (-not (Test-Path -LiteralPath (Join-Path $PlanDir 'private-scan-plan.json') -PathType Leaf)) {
            throw 'Run Prepare first; frozen plan not found.'
        }
        Write-Host '=== WP3-R6: RECHECK FULL AUDIO HASHES BEFORE NATIVE SCAN ==='
        & $Python $Adapter guard @Arguments --plan-dir $PlanDir
        if ($LASTEXITCODE -ne 0) { throw 'Frozen sources drifted; native scan forbidden.' }

        $Db=Join-Path $PlanDir 'native-features.sqlite'
        $Embeddings=Join-Path $PlanDir 'embeddings'
        if (Test-Path -LiteralPath $Db) {
            throw 'Native feature DB already exists. Do not overwrite or blindly retry.'
        }
        $present=@(Get-ChildItem -LiteralPath $Embeddings -Force)
        if ($present.Count -ne 0) {
            throw 'Embedding output folder not empty. Do not overwrite or blindly retry.'
        }
        Write-Host '=== WP3-R6: 240 ORIGINAL ESSENTIA C++ SONG ANALYSES ==='
        Write-Host 'Fixed native pipeline; workers auto is startup-only, max 8; no dynamic tuning.'
        # Stdout and stderr are PRIVATE: scanner may print track identities.
        $Log=Join-Path $PlanDir 'private-scanner-stdout.json'
        $Errors=Join-Path $PlanDir 'private-scanner-stderr.txt'
        $ScanArgs=@(
            'scan-features',
            '--tracks-file',(Join-Path $PlanDir 'exact-240-tracks.txt'),
            '--source-root',$SourceRoot,
            '--db',$Db,
            '--embedding-dir',$Embeddings,
            '--models-dir',$Models,
            '--models','moodtheme,genre,voice',
            '--audio-backend','essentia',
            '--essentia-worker',$Worker,
            '--workers','auto','--threads','1',
            '--max-errors','3','--json'
        )
        # Windows PowerShell 5.1 can promote *redirected* native stderr
        # to NativeCommandError if ErrorActionPreference is Stop, even
        # when the scanner reports success. Capture actual process exit
        # code; keep both native streams ONLY in private local files.
        $PriorErrorAction=$ErrorActionPreference
        $ScannerExit=-1
        try {
            $ErrorActionPreference='Continue'
            & $Scanner @ScanArgs 1> $Log 2> $Errors
            $ScannerExit=$LASTEXITCODE
        }
        finally {
            $ErrorActionPreference=$PriorErrorAction
        }
        if ($ScannerExit -ne 0) {
            throw 'Native scanner stopped; private logs and partial outputs retained. Do NOT restart blindly.'
        }
    }
    if ($Stage -eq 'Verify' -or $Stage -eq 'All') {
        Write-Host '=== WP3-R6: READ-ONLY COMPLETE SCAN VALIDATION ==='
        & $Python $Adapter verify @Arguments --plan-dir $PlanDir
        if ($LASTEXITCODE -ne 0) {
            throw '240-song native model/head/embedding check BLOCKED. Do NOT interpret metrics.'
        }
        Write-Host '=== WP3-R6: FROZEN RESEARCH-ONLY EVALUATION ==='
        $Aggregate=Join-Path $PlanDir 'aggregate-wp3-r6-frozen-teacher-evaluation.json'
        if (Test-Path -LiteralPath $Aggregate) {
            throw 'Aggregate already exists; refuse overwrite or repeat post-hoc evaluation.'
        }
        $EvaluationArgs=@(
            $Eval,
            '--plan-dir',$PlanDir,
            '--old-grouped-research-db',$OldGrouped,
            '--bliss-db',$Bliss,
            '--r5-manifest',$R5,
            '--frozen-protocol',$Frozen,
            '--out',$Aggregate
        )
        & $Venv @EvaluationArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'Frozen teacher-proxy evaluation blocked. Preserve native output unchanged.'
        }
        Write-Host "Aggregate report (no song identities): $Aggregate"
    }
    Write-Host '=== WP3-R6 STAGE COMPLETED ==='
    Write-Host "Private files never upload/commit: $PlanDir"
}
