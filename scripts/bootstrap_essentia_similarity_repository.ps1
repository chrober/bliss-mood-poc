& {
    $ErrorActionPreference = 'Stop'

    # Reproducible migration, never overwrites a branch or touches source/main.
    # For CI: set ESSENTIA_BOOTSTRAP_PREPARE_ONLY=1 and
    # ESSENTIA_BOOTSTRAP_SOURCE / ESSENTIA_BOOTSTRAP_OUTPUT.
    $SourceRepo = 'chrober/bliss-mood-poc'
    $SourceBranch = 'feat/general-pairwise-similarity-research'
    $TargetRepo = 'chrober/essentia-similarity'
    $TargetBranch = 'feat/bootstrap-rust-engine'
    $PrepareOnly = ($env:ESSENTIA_BOOTSTRAP_PREPARE_ONLY -eq '1')
    $Encoding = New-Object System.Text.UTF8Encoding($false)

    function Check {
        param([string] $Program, [string[]] $Arguments)
        & $Program @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Aufruf fehlgeschlagen: $Program $($Arguments -join ' ')"
        }
    }
    function ReadText {
        param([string] $Path)
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Datei fehlt: $Path"
        }
        [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    }
    function SaveText {
        param([string] $Path, [string] $Value)
        $Folder = Split-Path -Parent $Path
        if (-not (Test-Path -LiteralPath $Folder)) {
            $null = New-Item -Path $Folder -ItemType Directory -Force
        }
        [System.IO.File]::WriteAllText($Path, $Value, $Encoding)
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw 'git wird benoetigt.'
    }
    if (-not $PrepareOnly) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
            throw 'GitHub CLI (gh) wird benoetigt.'
        }
        Check gh @('auth', 'status')
        $CurrentUser = & gh api user --jq '.login'
        if ($LASTEXITCODE -ne 0 -or $CurrentUser.Trim() -ne 'chrober') {
            throw 'Aktive GitHub-Anmeldung muss chrober sein.'
        }
        Check gh @('auth', 'setup-git')
        Check gh @('repo', 'view', $TargetRepo, '--json', 'nameWithOwner')

        # GitHub returns empty output but success for a non-existent remote branch.
        $Branches = @(& git ls-remote --heads "https://github.com/$TargetRepo.git" "refs/heads/$TargetBranch")
        if ($LASTEXITCODE -ne 0) { throw 'Remote-Branch-Pruefung fehlgeschlagen.' }
        if ($Branches.Count -gt 0) {
            throw "Branch existiert bereits: $TargetBranch. Kein Force-Push."
        }
    }

    $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
        'essentia-bootstrap-' + [guid]::NewGuid().ToString('N'))
    $Source = if ($PrepareOnly -and $env:ESSENTIA_BOOTSTRAP_SOURCE) {
        $env:ESSENTIA_BOOTSTRAP_SOURCE
    } else {
        Join-Path $TempRoot 'source'
    }
    $Target = if ($PrepareOnly -and $env:ESSENTIA_BOOTSTRAP_OUTPUT) {
        $env:ESSENTIA_BOOTSTRAP_OUTPUT
    } else {
        Join-Path $TempRoot 'essentia-similarity'
    }
    if (Test-Path -LiteralPath $Target) {
        throw "Zielverzeichnis existiert bereits: $Target"
    }
    $null = New-Item -Path $TempRoot -ItemType Directory -Force

    if (-not ($PrepareOnly -and $env:ESSENTIA_BOOTSTRAP_SOURCE)) {
        Check gh @('repo', 'clone', $SourceRepo, $Source, '--',
            '--branch', $SourceBranch, '--single-branch')
    }
    if ($PrepareOnly) {
        $null = New-Item -Path $Target -ItemType Directory -Force
    } else {
        Check gh @('repo', 'clone', $TargetRepo, $Target, '--',
            '--branch', 'main', '--single-branch')
        Check git @('-C', $Target, 'switch', '-c', $TargetBranch)
    }

    $Old = Join-Path $Source 'research/lyrion-similarity-engine'
    $Core = ReadText (Join-Path $Old 'src/lib.rs')
    $Store = ReadText (Join-Path $Source 'src/feature_lookup.rs')
    $Shadow = ReadText (Join-Path $Old 'src/bin/shadow.rs')

    # The mathematical core is independent of any host or SQLite.
    $Core = $Core.Replace('lyrion-general-geometry-v1', 'essentia-similarity-geometry-v1')
    $Core = $Core.Replace('No audio, Lyrion dependencies', 'No audio, player dependencies')
    $Core = $Core.Replace('bliss_rank', 'baseline_rank')
    $Core = $Core.Replace('Bliss', 'the host baseline')
    if ($Core -match '(?i)bliss|lyrion|rusqlite|feature_lookup') {
        throw 'Core enthaelt unerwartete Host- oder Speicher-Kopplung.'
    }

    # Preserve the real scanner v3 SQL and decoder, but remove Bliss naming.
    $StoreHeader = @'
//! Exact opaque-key, read-only Mood/Genre feature lookup for SQLite v3.
//! Independent of any music player, playback and runtime audio inference.
'@
    $Store = [regex]::Replace($Store,
        '(?s)\A//! Strict, read-only retrieval.*?\r?\nuse anyhow::',
        $StoreHeader + [Environment]::NewLine + 'use anyhow::')
    $Store = $Store.Replace('exact Bliss track keys', 'exact sidecar track keys')
    $Store = $Store.Replace('exact Bliss track key', 'exact sidecar track key')
    if ($Store -match '(?i)bliss|lyrion') {
        throw 'Feature-Store enthaelt unerwarteten Bliss-/Lyrion-Bezug.'
    }

    $NewShadowHeader = @'
//! Read-only local Essentia feature SQLite v3 shadow comparison.
//! Opaque feature keys and admitted candidate ranks must come from the caller.
//! NOT an SPI v2 provider, playlist writer or calibrated General Metric.
use essentia_feature_store as feature_lookup;
'@
    $Pattern = '(?s)\A//! Research-only, local read-only adapter.*?\r?\nmod feature_lookup;'
    if (-not [regex]::IsMatch($Shadow, $Pattern)) {
        throw 'Shadow-Code hat sich geaendert. Migration nicht mehr sicher.'
    }
    $Shadow = [regex]::Replace($Shadow, $Pattern, $NewShadowHeader.TrimEnd())
    $Shadow = $Shadow.Replace('lyrion_similarity_engine_research', 'essentia_similarity_core')
    $Shadow = $Shadow.Replace('lyrion-general-sidecar-shadow', 'essentia-similarity-sidecar-shadow')
    $Shadow = $Shadow.Replace('lyrion-shadow-fictional', 'essentia-shadow-fictional')
    $Shadow = $Shadow.Replace('bliss_rank', 'baseline_rank')
    $Shadow = $Shadow.Replace('admitted_by_bliss', 'admitted_by_host')
    $Shadow = $Shadow.Replace('NEUTRAL_FULL_QUERY_BLISS_FALLBACK',
        'NEUTRAL_FULL_QUERY_BASELINE_FALLBACK')
    $Shadow = $Shadow.Replace('Bliss', 'host baseline')
    $Shadow = $Shadow.Replace('Lyrion', 'the host')
    $Shadow = $Shadow.Replace('TracksV2.File', 'feature_tracks.track_file')
    if ($Shadow -match '(?i)bliss|lyrion|src/feature_lookup\.rs|mod feature_lookup') {
        throw 'Shadow-Code ist noch mit dem alten Repository gekoppelt.'
    }

    $RootManifest = @'
[workspace]
resolver = "2"
members = [
    "crates/essentia-similarity-core",
    "crates/essentia-feature-store",
    "apps/essentia-similarity-shadow",
]
'@
    $CoreManifest = @'
[package]
name = "essentia-similarity-core"
version = "0.1.0"
edition = "2021"
license = "MIT"
publish = false
description = "Player-independent exploratory geometric music similarity"
'@
    $StoreManifest = @'
[package]
name = "essentia-feature-store"
version = "0.1.0"
edition = "2021"
license = "MIT"
publish = false
description = "Read-only Essentia classifier sidecar SQLite v3 accessor"

[dependencies]
anyhow = "1.0"
rusqlite = { version = "0.32", features = ["bundled"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
'@
    $ShadowManifest = @'
[package]
name = "essentia-similarity-shadow"
version = "0.1.0"
edition = "2021"
license = "MIT"
publish = false
description = "Research-only Essentia similarity shadow diagnostics"

[dependencies]
essentia-similarity-core = { path = "../../crates/essentia-similarity-core" }
essentia-feature-store = { path = "../../crates/essentia-feature-store" }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[dev-dependencies]
rusqlite = { version = "0.32", features = ["bundled"] }
'@
    $Readme = @'
# Essentia Similarity

Player-independent Rust research engine for general music similarity from
offline Essentia features. The code is NOT an approved production General
Metric, a trained Personal Metric, an LMS plugin, or a Guidance SPI v2 provider.

Three independent workspace crates:

- crates/essentia-similarity-core: pure, host- and SQLite-independent
  versioned cosine / per-vector centered cosine, bounded synthetic rank audits.
- crates/essentia-feature-store: read-only lookup for the actual scanner
  SQLite v3 feature_models and feature_tracks schema. Caller supplies exact
  opaque feature_tracks.track_file keys; no title/artist or LMS URL guessing.
- apps/essentia-similarity-shadow: CLI research-only whole-cohort, anonymized
  baseline vs experimental rank statistics with neutral fail-closed fallback.

Run: cargo test --workspace --all-targets
Run: cargo fmt --all -- --check
CLI: cargo run -p essentia-similarity-shadow -- --request PATH_TO_TRUSTED_JSON

CLI contract schema: essentia-similarity-sidecar-shadow-v1.
Required mode: shadow_only.
Trusted local fields: feature_database, anchor_track_file, model_id (genre
or moodtheme), metric (affine_cosine_v1 or affine_centered_cosine_v1),
expected_model_key, experimental_preview_opt_in (false by default).
Each candidate: unique candidate_id, exact track_file, baseline_rank
(0-based), admitted_by_host=true. Complete pool: 2..50.
Input must come from a trusted local host, never directly from browser input.
No playlist/queue/route writes or full-catalog candidate creation.

Source: chrober/bliss-mood-poc, branch
feat/general-pairwise-similarity-research, October 30 2026.
The original research source continues to own the offline Essentia scanner,
WP1 General Metric evaluation, WP2 Personal Metric experiments, and WP3
Bliss-Feature / Essentia-Feature correlations.

Future separate native SPI provider: chrober/bliss-guidance-essentia.
Future separately installable Lyrion provider:
chrober/lms-guidance-essentia.
Neither is implemented by this bootstrap.

Limitations: strict actual Essentia-reference validation may still be
outstanding for user features. Only sigmoid Genre87 and Mood56 heads are
supported. No Embedding1280 generic sidecar or calibrated cross-head
fusion. No inference at playlist runtime. No actual listening-quality
claim. Licenses for Essentia and third-party ONNX models must be reviewed
independently before distributing binaries or model weights. This repo
does not bundle Essentia, audio or ONNX files.
'@
    $Workflow = @'
name: Rust workspace CI

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: [[MATRIX]]
    timeout-minutes: 25
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt
      - uses: Swatinem/rust-cache@v2
      - name: Test complete workspace
        shell: bash
        run: |
          set -euo pipefail
          cargo test --workspace --all-targets
      - name: Rustfmt check
        shell: bash
        run: |
          set -euo pipefail
          cargo fmt --all -- --check
'@
    $Workflow = $Workflow.Replace('[[MATRIX]]', '$' + '{{ matrix.os }}')

    SaveText (Join-Path $Target 'Cargo.toml') $RootManifest
    SaveText (Join-Path $Target 'crates/essentia-similarity-core/Cargo.toml') $CoreManifest
    SaveText (Join-Path $Target 'crates/essentia-similarity-core/src/lib.rs') $Core
    SaveText (Join-Path $Target 'crates/essentia-feature-store/Cargo.toml') $StoreManifest
    SaveText (Join-Path $Target 'crates/essentia-feature-store/src/lib.rs') $Store
    SaveText (Join-Path $Target 'apps/essentia-similarity-shadow/Cargo.toml') $ShadowManifest
    SaveText (Join-Path $Target 'apps/essentia-similarity-shadow/src/main.rs') $Shadow
    SaveText (Join-Path $Target '.github/workflows/rust-ci.yml') $Workflow
    SaveText (Join-Path $Target '.gitignore') ('/target/' + [Environment]::NewLine)
    SaveText (Join-Path $Target 'README.md') $Readme

    if (Get-Command cargo -ErrorAction SilentlyContinue) {
        Check cargo @('fmt', '--manifest-path', (Join-Path $Target 'Cargo.toml'), '--all')
        Check cargo @('test', '--manifest-path', (Join-Path $Target 'Cargo.toml'),
            '--workspace', '--all-targets')
    } elseif (-not $PrepareOnly) {
        Write-Warning 'Cargo fehlt lokal: GitHub-CI muss Build und Formatierung pruefen.'
    }

    if ($PrepareOnly) {
        Write-Host "Lokaler eigenstaendiger Workspace vorbereitet: $Target" -ForegroundColor Green
        Write-Host 'Kein GitHub-Repository veraendert.'
        return
    }

    Check git @('-C', $Target, 'add', 'Cargo.toml', 'crates', 'apps',
        '.github', '.gitignore', 'README.md')
    Check git @('-C', $Target, 'commit', '-m',
        'feat: bootstrap independent Essentia Similarity Rust workspace')
    Check git @('-C', $Target, 'push', '-u', 'origin', $TargetBranch)

    $Body = @'
Research-only migration from chrober/bliss-mood-poc.
Independent Rust geometry core, read-only SQLite v3 feature store, and
whole-query neutral shadow CLI. Linux/Windows CI, original synthetic tests.
Host-specific Bliss identity/rank naming removed from reusable core.
No real General Metric validation, Personal model, guidance SPI v2 provider,
Lyrion plugin, playlist writes, ONNX or Essentia binaries included.
Follow-ups: exact external identity resolver; actual source parity; provider
describe/prepare/score/close and Lab shadow bridge.
'@
    Check gh @('pr', 'create', '--repo', $TargetRepo, '--base', 'main',
        '--head', $TargetBranch, '--draft',
        '--title', 'Bootstrap independent Essentia Similarity Rust workspace',
        '--body', $Body)
    Write-Host 'Draft PR im neuen Repository erstellt.' -ForegroundColor Green
    Write-Host 'Weder alte Source-Branches noch main wurden geaendert.'
}
