# FMA-Small: bounded, verified GitHub Actions audio cache

**Status:** October 21, 2026, research branch
`feat/similarity-metric-evaluation`, Draft PR #16.

## Why not cache the complete 7.2-GiB archive?

The official `fma_small.zip` is approximately 7.2 GiB.
GitHub Actions' default per-repository cache limit is 10 GB
(configurable, potentially billable above included capacity).
Caching the entire original archive could evict existing
Cargo/Rust and model caches, or generate additional costs.
The previous FMA-80 paired A/B run spent **243.87 s**
downloading the archive alone.

Official source: https://github.com/mdeff/fma.
Cache documentation: https://docs.github.com/en/actions/reference/dependency-caching-reference.

## Design: source-pinned selected-song cache

Implementation:
[`scripts/fma_selected_audio_cache.py`](../scripts/fma_selected_audio_cache.py).

1. **Cold run:** Download the publisher's original FMA archive once.
   Verify the full source SHA256
   `f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c`
   against the value registered in the successful FMA A/B experiment.
2. Use TRAINING/VALIDATION catalogue metadata only;
   leave official FMA TEST rows untouched. Preserve the
   deterministic ordered sample, `seed=20261021`,
   eight Genres times ten VALIDATION tracks. Exclude 42
   possible MTG-Jamendo artist/title catalogue matches in
   the screened study. Preserve the **original analyzed
   sample fingerprint** rather than resampling from
   the 80 tracks remaining in the new archive.
3. Create a **branch-scoped Actions cache** containing only
   a selected-song ZIP with the required 80 MP3 excerpts
   and a corresponding source/sample manifest.
   The manifest stores original publisher ZIP SHA,
   metadata/MTG hashes, selected IDs/sample digest,
   Genres/seed/filter policy, and **SHA256 per MP3**.
   Selected clip identifiers remain inside the cache
   and must not appear in Git commits, uploaded
   artifacts, or public logs.
4. Remove the original 7.2-GiB ZIP from temporary runner
   storage once packaging is complete.
   `actions/cache/save@v4` saves only
   `fma-private/fma-selected-cache`, never the full archive.
5. **Warm run:** Restore with `actions/cache/restore@v4`.
   Fail closed if source fingerprints, individual MP3s,
   artist uniqueness, Genre distribution, frozen sample,
   or repeated MTG catalogue screen do not match.
   Cache misses fall back to the official publisher
   download; corrupt hits never silently change the audio.
6. `benchmark_fma_genre.py` and
   `evaluate_fma_embedding_ab.py` accept an optional
   `--selected-cache-manifest`. Without it, the original
   full-ZIP execution remains available. With it,
   the aggregate report still cites the **original
   FMA audio archive SHA**, additionally recording
   the selection ZIP SHA. Old Genre baselines must
   reproduce exactly.
7. Record real `cache-hit` state, selected ZIP size,
   download and inference durations in
   `GITHUB_STEP_SUMMARY`. Never claim performance
   improvement before observing both a successful cold
   run and a successful warm restore.

The [paired FMA research workflow](../.github/workflows/research-fma-embedding-ab.yml)
uses the branch-specific
`fma-small-screened80-selected-v1-f923...` cache key.

### Storage, access and licensing

A GitHub Actions **cache is not a confidential or
licence-protected archive**. Public repositories,
branch inheritance, and pull-request accessibility
make original-recording rights important. Do not put
selected audio into `actions/upload-artifact`,
Git LFS, releases, or distribution packages.
Only publicly offered research FMA clips may be
used for the documented experiment; never include
audio from the user's local music library.
Respect the individual FMA Creative Commons licences.
Do not expose audio to untrusted workflows or
copy cache contents outside the research context.
Retention and eviction are normal.

A full-archive cache is a poor default given
the 10-GB quota and rights/access concerns.
A different sample, seed, or screen policy must
use a separate versioned cache key; never let
a changed cohort silently appear as historical
reproduction.

### Verification gates

[`tests/test_fma_selected_audio_cache.py`](../tests/test_fma_selected_audio_cache.py)
uses synthetic FMA-style ZIP fixtures including an
invalid official TEST row. It tests cold packing,
warm verified restoration without the full original
source, sample fingerprints, ZIP/MP3 corruption,
changed metadata, and no overwrite. Linux and
Windows tests cover the cache code.

## Measured evidence: cold creation and warm restore

**Cold run PASS:**
[GitHub Actions 39632517381](https://github.com/chrober/bliss-mood-poc/actions/runs/39632517381).
The 7.2-GiB publisher download took **246.39 s**.
The tool selected from 7,197 usable FMA development
audio members (three size anomalies rejected).
Its checksum-verified `selected.zip` contained
**76.51 MiB** for the frozen set of 80 songs;
the full publisher ZIP was not cached.
The original Genre and new 1280D A/B evaluations
also passed on the same sample.

**Warm cross-workflow restore PASS:**
[Screened Genre run 39633485262](https://github.com/chrober/bliss-mood-poc/actions/runs/39633485262).
The log confirms `Cache hit for:
fma-small-screened80-selected-v1-f923...`,
and the step downloading the 7.2-GiB original
was **skipped**. The restored ZIP and
all 80 MP3 SHA256 values were verified;
the bundle still measured **76.51 MiB**.
Original Genre scoring passed unchanged.

This eliminates the **publisher download cost on
cache hits**, but is **not a directly controlled
cold-vs-warm total-runtime comparison** because
the workflows and Rust binary cache states differed.
After cache eviction, the workflow correctly
falls back to the publisher.
