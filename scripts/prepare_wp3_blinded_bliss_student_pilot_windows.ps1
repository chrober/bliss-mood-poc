& {
    # Research-only BLIND 24 pair diagnostic using old 100 songs for model
    # fitting and new 240 songs for Bliss-only inference. No audio/network.
    # Windows PowerShell 5.1/7, existing Python 3.15 and pinned WP3 venv.
    $ErrorActionPreference='Stop'
    Set-StrictMode -Version Latest

    $repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $branch=(& git -C $repo branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -cne 'feat/general-pairwise-similarity-research') {
        throw 'Only the isolated research branch is allowed.'
    }
    $python=(Get-Command python -ErrorAction Stop).Source
    $version=@(& $python --version)
    if ($LASTEXITCODE -ne 0 -or ($version -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Existing Python 3.15 is required; no fallback or installation.'
    }
    $priorRoot=Join-Path $repo 'benchmark-wp3-research-20261030-091600-8c93d55f'
    $metadataRoot=Join-Path $repo 'benchmark-wp3-research-20261030-064618-7f8c43a3/lyrion-metadata-eeedcd9630e04da3a3c046db974b33f8'
    $sources=@{
        bliss=Join-Path $repo 'bliss.db'
        snapshot=Join-Path $metadataRoot 'artist-repeat-identities.sqlite'
        library=Join-Path $metadataRoot 'library.db'
        old=Join-Path $priorRoot 'wp3-research.sqlite'
        manifest=Join-Path $repo 'benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc/private-independent-cohort.json'
        spec=Join-Path $repo 'research/wp3-moodtheme-student-candidate-v1.json'
        script=Join-Path $repo 'scripts/prepare_wp3_blinded_bliss_student_pilot.py'
        venvPython=Join-Path $priorRoot 'venv/Scripts/python.exe'
    }
    foreach($key in $sources.Keys) {
        if (-not (Test-Path -LiteralPath $sources[$key] -PathType Leaf)) {
            throw "Known source missing ($key); no automatic search/scan."
        }
    }
    $envVersion=@(& $sources.venvPython --version)
    if ($LASTEXITCODE -ne 0 -or ($envVersion -join '').Trim() -notmatch '^Python 3\.15(?:\.|$)') {
        throw 'Original research virtual environment must use Python 3.15.'
    }
    $nonce=[guid]::NewGuid().ToString('N')
    $dest=Join-Path $repo ('benchmark-wp3-blind-student-pilot-' + $nonce)
    if (Test-Path -LiteralPath $dest) { throw 'Refuse non-new output directory.' }
    Write-Host '=== WP3: BLIND STUDENT VERSUS ORIGINAL BLISS PILOT ==='
    Write-Host 'Fit fixed Ridge only on existing 100 development songs.'
    Write-Host 'Use 240 new Bliss-only songs: NO Essentia/ONNX/audio inference.'
    $args=@(
        $sources.script,
        '--bliss-db',$sources.bliss,
        '--repeat-identity-db',$sources.snapshot,
        '--lyrion-library-db',$sources.library,
        '--old-grouped-research-db',$sources.old,
        '--new-private-manifest',$sources.manifest,
        '--frozen-spec',$sources.spec,
        '--out-dir',$dest)
    & $sources.venvPython @args
    if ($LASTEXITCODE -ne 0) { throw 'Blinded pilot generation was blocked.' }
    Write-Host '=== COMPLETED (PRIVATE, NO LABELS COLLECTED) ==='
    Write-Host "Optional blind review CSV (do NOT upload): $(Join-Path $dest 'private-blind-pairs.csv')"
    Write-Host "PRIVATE trained student (do NOT upload): $(Join-Path $dest 'private-frozen-student.json')"
    Write-Host "SEALED audit (do NOT inspect until rating): $(Join-Path $dest 'private-sealed-selection-audit.json')"
    Write-Host 'No Lyrion queue, audio scan, human judgments or metric promotion.'
}
