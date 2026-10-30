# WP1-E2: MTT 1,019-clip source/cache recovery diagnostics (30 October 2026)

## Actual root-cause evidence, not a similarity-quality result

The last full MTT global equal-weight pairwise fusion attempt was [GitHub Actions 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086), on the isolated feat/general-pairwise-similarity-research branch. Actual job logs show:

- The branch-scoped curated 1,019-MP3 cache lookup returned **Cache not found** for the previously used immutable key mtt-1019-clips-v1-cf210e087ed5-cb6108a10d3a-2972769864.
- The historical successful 1,019-clip experiment [39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040) ran instead on sibling feat/similarity-metric-evaluation. According to the [official GitHub Actions cache isolation rules](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching), sibling branch caches are **not** accessible merely by supplying the same cache key.
- Publisher metadata and bounded official multipart ZIP-directory requests succeeded in the failed experiment, but the subsequent sparse MP3 member download returned curl code 28 / HTTP 000 on part 1. No new global-fusion metric was produced.
- Successful historical [WP1-E1 audit](wp1-e1-verified-public-benchmark-evidence-20261030.md) confirmed that historical artifact files contain aggregate metrics only, **not enough per-song feature vectors to reconstruct the new global pairwise fusion scores**.
- Do NOT silently create or publish a new GitHub audio cache or copy archives between research branches to bypass licensing/access boundaries. No full 2.77-GiB archive download, no unverified mirror, no user-library tracks, no PR #16/main changes.

## New exact, bounded source-availability protocol

Added [source probe](../scripts/probe_wp1_e2_mtt_source.py), [its synthetic tests](../tests/test_probe_wp1_e2_mtt_source.py), [one-member CRC test](../scripts/probe_wp1_e2_mtt_member.py), [its synthetic tests](../tests/test_probe_wp1_e2_mtt_member.py) and dedicated [GitHub Actions diagnostics](../.github/workflows/research-wp1-e2-source-diagnostic.yml).

The diagnostic workflow has no access to models, production Lyrion, or private audio and performs **no inference**. It reads only the exact official https://mirg.city.ac.uk/datasets/magnatagatune/ site:

1. Run Python 3.15 offline network-protocol and fail-closed tests on Linux and Windows.
2. Perform a lookup-only Actions cache request in the current branch; never download/save licensed content through the diagnostic cache step.
3. Check exactly one 4,096-byte HTTP Range request on EACH of the three multipart archive parts; require status 206, exact Content-Range, unchanged identity encoding, expected bounded content length, unchanged URL and plausible part byte count. Total requested payload is **12 KiB**.
4. Only when all tiny range checks PASS, download official comparisons CSV, clip catalog and **exactly 8 MiB of last-part central-directory tail** to a temporary runner directory (not an artifact).
5. Independently validate official metadata SHA256, exact 346 unique questions / 1,019 selected clips and source ZIP directory. Use a deterministic single referenced clip only: retrieve its bounded original archive member span, parse original ZIP header, verify decompressed size and CRC in memory; never save or publish audio, song names, embeddings, models, scores, or listener-vote rows.
6. Report anonymized counts and whether one tested MP3 range succeeded. **One success is NOT 1,019-success reproducibility; an HTTP 206 tiny probe is NOT evidence of actual member availability.** The output artifact contains only small JSON status reports.

The script reports errors without exposing the selected clip identity or original path. A one-clip transport failure is a non-claim, not a bad fusion result. All tests are synthetic and cannot substitute a real network probe.

### Verified first diagnostic: 41059898084

[First successful live diagnostic](https://github.com/chrober/bliss-mood-poc/actions/runs/41059898084) (30 October 2026):

- Linux and Windows synthetic tests: PASS.
- Current-branch cache lookup: **MISS**.
- Original publisher mp3.zip.001, mp3.zip.002 and mp3.zip.003: all returned correctly bounded **HTTP 206** for 0..4095 bytes.
- Publisher-reported part lengths: 1,100,000,000 / 1,100,000,000 / 772,769,864 bytes.
- No MP3 complete-member download, embedding inference, or fusion evaluation performed in this initial gate.

This establishes that a tiny source Range probe works, **not** that 1,019 sparse clip downloads will work. The expanded same-branch CRC one-member test is the next source diagnostic and is separately labelled.

### Verified second diagnostic: 41060333623

[GitHub Actions 41060333623](https://github.com/chrober/bliss-mood-poc/actions/runs/41060333623) **PASS** on Linux/Windows synthetic gates and real network:
- Current-branch cache again absent, all three official 4-KiB multipart probes PASS.
- Official comparisons, clip catalog SHA256 and 8-MiB archive tail validated.
- One deterministically selected member from the registered 1,019 clips fetched with **one** HTTP-206 Range request (116,178 bytes), verified against its ZIP local header, original decompressed member length and CRC.
- **No new MTT similarity results**: one authenticated clip demonstrates the exact sparse source implementation works, but does not prove 1,019 clips or long-running source availability.

The extended [same-branch 30-clip stress gate](../.github/workflows/research-wp1-e2-source-diagnostic.yml) now selects ten registered clips per each archive part, interleaves them, enforces original 3.5-second request spacing, CRC-checks every individual clip, and reports only counts/failure reason. No audio or per-track identifiers are saved as artifacts. Its success or partial stop must not be described as a full public MTT fusion evaluation.

## Scientific next action once source is sufficiently reliable

Only when source access (or an independently documented lawful, checksum-verified existing curated cache) is verified should the predeclared [global pair-fusion MTT runner](../.github/workflows/research-global-pair-fusion-mtt.yml) be attempted. Require the identical 1,019 clips and 293 decisive human triplets, same original Genre87/Mood56/Embedding1280, all four fixed globally comparable pairwise fusion scores, complete coverage/tie rates, paired discordance/sensitivity and original baseline replays. No trained weights, no changed metric choices, no fake holdout, no new manual listening. Keep FMA TEST untouched; DEAM and FMA external tasks stay separate.

**Current scientific status:** WP1-E1 real aggregate replay PASSED. WP1-E2 new global pairwise MTT audio experiment remains **UNMEASURED** until a full, CRC-verified 1,019-clip audio/features replay succeeds. WP3-R6/R7 teacher reconstruction does not substitute for independent musical similarity; WP2 optional Personal Metric remains a parallel research strand.
