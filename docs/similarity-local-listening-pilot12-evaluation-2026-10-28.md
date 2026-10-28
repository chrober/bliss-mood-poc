# Local 12-pair ordinal listening-pilot evaluation (2026-10-28)

**Scope:** General-purpose untrained song-similarity research in Draft PR #16.
Personalized metric learning is an optional separate track. No general
production winner has been established.

## Verified local study state

The user's first 12-pair listening pilot has 24 distinct tracks and
all 60 numeric human rating fields complete, with seven comments.
The submitted Excel CSV uses **tab delimiters and Windows-1252**
rather than comma/UTF-8. The sealed local selection-audit-private.json
contains the five frozen model-score columns, exact matching original
song keys, sampling strata and pair order. No private song identities,
notes, vectors or scores are copied to this repository.

Human pair 10 included a **spoken interview/comment instead of music**.
Its original ratings must not be rewritten or silently discarded.
Flag it explicitly and report both the full 12 pairs and a
music-only 11-pair sensitivity analysis.

## Reproducible ordinal evaluator

[scripts/evaluate_local_listening_pilot.py](../scripts/evaluate_local_listening_pilot.py)
reads Excel UTF-8 or CP1252 with comma, semicolon or tab delimiters,
checks valid completed ordinal human scores and checks exact ordered
left/right song identities against the original sealed model audit.

The five compared model scores are Genre cosine, Genre centered
cosine, Mood cosine, Mood centered cosine and 1280D audio-embedding
cosine. The four human outcomes are Genre/Style, Mood/Energy,
Timbre and directed left-to-right next-track suitability.

For each of the 20 comparisons the program computes **tie-aware
Spearman rho, Kendall tau-b, concordance/discordance/ties,
leave-one-pair-out Spearman range and three largest rank
disagreements** indexed by pair number. It does this separately
for all 12 pairs and for the 11 music-only pairs.

Only a **new local ignored folder** is created, with
aggregate-model-comparison.json and numbered-pair-details-private.csv.
Neither file contains track paths, song names or original comments.
The report and console provide only numbered-pair diagnostics
and anonymous aggregate scores. No ONNX, music decoding,
feature-database writes, network requests or Lyrion changes occur.

## Windows PowerShell invocation

Start on a clean local checkout of feat/similarity-metric-evaluation.
The script below checks this branch, fast-forwards it,
checks that the two private input files exist and refuses
to overwrite an existing local report folder.

~~~powershell
& {
    $ErrorActionPreference = 'Stop'

    $Repo = 'D:\LMS\bliss-mood-poc'
    $Branch = 'feat/similarity-metric-evaluation'
    $Pilot = Join-Path $Repo 'benchmark-local-blinded-ab-pilot12-20261021'
    $Script = Join-Path $Repo 'scripts\evaluate_local_listening_pilot.py'
    $Ratings = Join-Path $Pilot 'listening-pairs.csv'
    $Audit = Join-Path $Pilot 'selection-audit-private.json'
    $Out = Join-Path $Repo 'benchmark-local-listening-eval12-20261028'

    Push-Location -LiteralPath $Repo
    try {
        $Current = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0 -or $Current -cne $Branch) {
            throw "Expected branch: $Branch"
        }
        & git pull --ff-only origin $Branch
        if ($LASTEXITCODE -ne 0) { throw 'Git pull failed.' }

        foreach ($InputFile in @($Script, $Ratings, $Audit)) {
            if (!(Test-Path -LiteralPath $InputFile -PathType Leaf)) {
                throw 'Research script, human ratings or private original audit is missing.'
            }
        }
        if (Test-Path -LiteralPath $Out) {
            throw 'Output directory already exists. No overwrite permitted.'
        }

        $Arguments = @(
            $Script,
            '--ratings', $Ratings,
            '--selection-audit', $Audit,
            '--nonmusic-pairs', '10',
            '--out-dir', $Out
        )
        & python @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw 'Evaluation failed. Never overwrite or upload private inputs.'
        }
        Write-Host 'Aggregate report:' (Join-Path $Out 'aggregate-model-comparison.json')
        Write-Host 'Numbered diagnostic report:' (Join-Path $Out 'numbered-pair-details-private.csv')
    }
    finally {
        Pop-Location
    }
}
~~~

Never upload the original listening CSV, selection-audit-private.json,
user music, private feature sidecars, SQLite or any song paths to
GitHub, Actions or issues. The aggregate model-correlation matrix
alone may be voluntarily shared for interpretation.

## Evidence limits and next steps

This is a **model-selected sample of 12** with one human listener,
not a random generalization study or independent model-selection
holdout. The model-selection hypotheses are not ground truth.
An audio-pair similarity score is symmetric, unlike the
directed playlist-transition rating. A rank correlation here
is not a scientifically validated universal metric; differences
in single-pair sensitivity, ties, or the flagged nonmusic track
could reverse any provisional ranking. Do not tune a general
fusion on these 12 ratings and then evaluate on those same labels.
Freeze a disjoint, more representative listening study alongside
external MTT/FMA/DEAM benchmark evidence.

Related: [current chat handover](chat-handover.md),
[local cohort and listening runbook](similarity-local-library-retest-plan-2026-10-21.md),
[mandatory general-first and optional personal blending](similarity-general-personal-blending-architecture.md).
