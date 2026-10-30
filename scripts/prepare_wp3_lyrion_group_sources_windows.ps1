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
        # NEVER stream a Windows PowerShell here-string to BusyBox sh -s:
        # PS 5.1 native pipeline encoding can leave CR in the first
        # "set -eu" line, yielding "sh: set: illegal option -".
        # Only short ASCII, single-line remote commands are transmitted.
        # Every token is an invariant literal or a locally generated GUID.
        if ($stage -cnotmatch '^/tmp/wp3-metadata-[0-9a-f]{32}$') {
            throw 'Refusing an unexpected remote temporary path.'
        }
        $remoteLibrary = '/usr/local/slimserver/Cache/library.db'
        $remoteIdentity = '/usr/local/slimserver/Cache/BlissMixerLab/artist-repeat-identities.sqlite'
        $remoteCommands = @(
            "test -r $remoteLibrary",
            "test -r $remoteIdentity",
            "mkdir -m 700 $stage",
            # SQLite CLI dot command does not require shell quotes for
            # these GUID paths. Source is opened read-only, destination
            # is created only in the new private /tmp directory.
            "umask 077; echo .backup $stage/library.db | sqlite3 -readonly -batch -bail $remoteLibrary",
            "umask 077; echo .backup $stage/artist-repeat-identities.sqlite | sqlite3 -readonly -batch -bail $remoteIdentity",
            "test -s $stage/library.db",
            "test -s $stage/artist-repeat-identities.sqlite"
        )
        $remoteAttempted = $true
        foreach ($remoteCommand in $remoteCommands) {
            if ($remoteCommand -match '[\r\n]') {
                throw 'Refusing multi-line remote shell command.'
            }
            & ssh -T -o BatchMode=yes -o ConnectTimeout=8 $target $remoteCommand
            if ($LASTEXITCODE -ne 0) {
                throw 'Pi SQLite backup failed on a bounded remote step; no live databases modified.'
            }
        }
        Write-Host 'PI SQLITE ONLINE BACKUPS READY'

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
            $cleanup = "if test -d $stage; then rm -f $stage/library.db $stage/library.db-wal $stage/library.db-shm $stage/artist-repeat-identities.sqlite $stage/artist-repeat-identities.sqlite-wal $stage/artist-repeat-identities.sqlite-shm && rmdir $stage; fi"
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
