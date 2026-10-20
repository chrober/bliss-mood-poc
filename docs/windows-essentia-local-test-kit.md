# Windows x64 Essentia C++ CLI development test kit

Purpose: Use the real Windows bliss-mood.exe scanner with the original Essentia
C++ worker to generate experimental schema-v3 feature sidecars for the
separate PR #16 similarity research. NOT PRODUCTION APPROVED.

## Download and unpack

Open https://github.com/chrober/bliss-mood-poc/actions/workflows/native-essentia-windows.yml
Open the most recent successful run on draft PR #17 and download the artifact
named bliss-mood-essentia-windows-x64-dev from its Artifacts section.
Extract it to D:\LMS\essentia-cli-test or another local directory.

The kit contains bliss-mood.exe; essentia-worker/bliss-essentia-worker.exe
plus all packaged native DLLs and worker-dependencies.json; an optional
external ONNX Runtime DLL if required; scripts/download-models.ps1;
BUILD-PROVENANCE.txt, NATIVE-PROVENANCE.json, THIRD-PARTY-NOTICES, and
pacman-package-lock-observed.txt. The native worker should not be moved
out of its directory because its DLLs and SHA256 manifest must remain adjacent.

The archive deliberately omits model weights, private music, and databases.

## Download models (PowerShell)

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $kit = 'D:\LMS\essentia-cli-test'
    Set-Location $kit
    & '.\scripts\download-models.ps1'
    if (-not (Test-Path '.\models\discogs-effnet-bsdynamic-1.onnx')) {
        throw 'Missing EffNet model; check model downloads'
    }
}
```

## Small Windows library scan (PowerShell)

Replace the paths with your actual local Bliss source DB and NAS music root.
Use a fresh dedicated sidecar: never overwrite the original bliss.db or an
existing Rust-generated sidecar. The first scan deliberately uses 2 workers.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $kit = 'D:\LMS\essentia-cli-test'
    $bliss = 'D:\LMS\bliss-mood-poc\bliss.db'
    $music = '\\192.168.1.100\music'
    $sidecar = 'D:\LMS\essentia-features-test.db'
    if (Test-Path $sidecar) { throw 'Choose a fresh sidecar path' }
    $exe = Join-Path $kit 'bliss-mood.exe'
    $worker = Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'
    $arguments = @(
        'scan-features', '--bliss-db', $bliss, '--db', $sidecar,
        '--models-dir', (Join-Path $kit 'models'),
        '--models', 'genre,moodtheme,voice', '--source-root', $music,
        '--audio-backend', 'essentia', '--essentia-worker', $worker,
        '--workers', '2', '--threads', '1', '--max-new', '20',
        '--max-errors', '2', '--json'
    )
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Windows Essentia scan failed' }
}
```

Once generated, use the UNMODIFIED PR #16 evaluate_similarity.py on the
new sidecar with --include-experimental; the similarity research remains
entirely in your separate chat. Do not mix Rust and native model cohorts.

## Licensing and provenance limitations

This is an experimental development-only test kit, NOT a production release.
The original Essentia software is under AGPL terms; FFmpeg and the other
MinGW DLL dependencies have independent licenses and source obligations.
Per-DLL origins, exact MSYS2 owner/package versions and available notice
files are included. The manifest deliberately keeps
license_inventory_complete=false and release_approved=false.
Machine-collected provenance is NOT a legal audit or proof of compliance
with complete-source/redistribution requirements. Audit before any
production release or redistribution beyond this development evaluation.

No changes to PR #16, main, BlissMixerLab or the user's audio corpus.
