& {
    # WP3 read-only Pi metadata snapshot + local exact-source group preflight.
    # Windows PowerShell 5.1/7; existing Python 3.15 only; no audio or LMS changes.
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest

    $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $python = (Get-Command python -ErrorAction Stop).Source
    $version = @(& $python --version)
    if ($LASTEXITCODE -ne 0 -or ($version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Use the existing Python 3.15 (no fallback).'
    }
    $validator = Join-Path $repo 'scripts\verify_wp3_copied_lyrion_sqlite.py'
    $groupScript = Join-Path $repo 'scripts\derive_lyrion_research_groups.py'
    if (-not (Test-Path -LiteralPath $validator -PathType Leaf) -or
        -not (Test-Path -LiteralPath $groupScript -PathType Leaf)) {
        throw 'Missing WP3 scripts. Pull research branch first.'
    }

    # CI validation tests argument forwarding without contacting a remote host.
    if ($env:LYRION_WP3_METADATA_CI_VALIDATE_ONLY -eq '1') {
        if ($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_OS -cne 'Windows') {
            throw 'CI validation mode is restricted to Windows GitHub Actions.'
        }
        $ciArgs = @($validator,
            '--lyrion-library-db', [string]$env:LYRION_WP3_CI_LIBRARY_DB,
            '--repeat-identity-db', [string]$env:LYRION_WP3_CI_IDENTITY_DB)
        & $python @ciArgs
        if ($LASTEXITCODE -ne 0) { throw 'CI metadata SQLite validation failed.' }
        Write-Host 'PowerShell-to-Python argument preservation: PASS'
        return
    }

    $expectedBranch = 'feat/general-pairwise-similarity-research'
    $currentBranch = (& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $currentBranch -cne $expectedBranch) {
        throw "Expected branch: $expectedBranch"
    }
    foreach ($exe in @('ssh','scp','git')) {
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
            throw "Missing executable: $exe"
        }
    }
    $target = 'tc@192.168.1.111'
    $research = Join-Path $repo 'benchmark-wp3-research-20261030-064618-7f8c43a3'
    $bliss = Join-Path $repo 'bliss.db'
    $features = Join-Path $repo 'benchmark-native-similarity-100-20261029\native-features.sqlite'
    foreach ($path in @($research,$bliss,$features)) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Verified historical WP3 source missing: $path"
        }
    }

    $nonce = [guid]::NewGuid().ToString('N')
    $stage = '/tmp/wp3-metadata-' + $nonce
    $destination = Join-Path $research ('lyrion-metadata-' + $nonce)
    $library = Join-Path $destination 'library.db'
    $identity = Join-Path $destination 'artist-repeat-identities.sqlite'
    $remoteAttempted = $false
    $localCreated = $false
    $locallyValidated = $false
    try {
        Write-Host '=== PI: CONSISTENT SQLITE ONLINE BACKUPS ==='
        # Same transport and sqlite3 -readonly .backup as previous successful step.
        $backup = @'
set -eu
umask 077
STAGE=__STAGE__
LIB=/usr/local/slimserver/Cache/library.db
SNAP=/usr/local/slimserver/Cache/BlissMixerLab/artist-repeat-identities.sqlite
test -r "$LIB"
test -r "$SNAP"
mkdir -m 700 "$STAGE"
sqlite3 -readonly -batch -bail "$LIB" ".backup '$STAGE/library.db'"
sqlite3 -readonly -batch -bail "$SNAP" ".backup '$STAGE/artist-repeat-identities.sqlite'"
test -s "$STAGE/library.db"
test -s "$STAGE/artist-repeat-identities.sqlite"
echo WP3_REMOTE_BACKUPS_READY
'@
        $backup = $backup.Replace('__STAGE__',$stage)
        $remoteAttempted = $true
        $output = @($backup | & ssh -T -o BatchMode=yes -o ConnectTimeout=8 $target sh -s)
        if ($LASTEXITCODE -ne 0 -or $output -notcontains 'WP3_REMOTE_BACKUPS_READY') {
            throw 'Remote metadata backup failed.'
        }

        Write-Host '=== SECURE COPY TO UNIQUE PRIVATE WINDOWS DIRECTORY ==='
        New-Item -ItemType Directory -Path $destination -ErrorAction Stop | Out-Null
        $localCreated = $true
        & scp -q -o BatchMode=yes -o ConnectTimeout=8 "$($target):$stage/library.db" $library
        if ($LASTEXITCODE -ne 0) { throw 'SCP library.db failed.' }
        & scp -q -o BatchMode=yes -o ConnectTimeout=8 "$($target):$stage/artist-repeat-identities.sqlite" $identity
        if ($LASTEXITCODE -ne 0) { throw 'SCP artist-repeat-identities.sqlite failed.' }

        Write-Host '=== LOCAL SQLITE VALIDATION VIA PYTHON SCRIPT FILE ==='
        $checkArgs = @($validator,'--lyrion-library-db',$library,
                     '--repeat-identity-db',$identity)
        & $python @checkArgs
        if ($LASTEXITCODE -ne 0) { throw 'Local copied SQLite validation failed.' }
        $locallyValidated = $true

        Write-Host '=== WP3 READ-ONLY EXACT GROUP PRE-FLIGHT ==='
        $groupArgs = @($groupScript,
            '--bliss-db',$bliss,'--feature-db',$features,
            '--repeat-identity-db',$identity,'--lyrion-library-db',$library,
            '--seed','20261029','--limit','100','--preflight')
        & $python @groupArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'Source/group preflight incompatible (local copies retained).'
        }
        Write-Host '=== END: NO AUDIO SCAN OR TEACHER FIT ==='
        Write-Host "Private local metadata snapshots (DO NOT UPLOAD): $destination"
    }
    finally {
        if ($remoteAttempted) {
            Write-Host '=== REMOVING ONLY NEW TEMPORARY PI COPIES ==='
            # One-line remote command, no multiline fi/end-of-file transport.
            $cleanup = "if test -d $stage; then rm -f $stage/library.db $stage/artist-repeat-identities.sqlite && rmdir $stage; fi"
            & ssh -T -o BatchMode=yes -o ConnectTimeout=8 $target $cleanup
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Remote cleanup not confirmed: $stage"
            }
        }
        if ($localCreated -and -not $locallyValidated) {
            # Only remove the newly created incomplete UUID folder.
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
    }
}
