# Lyrion Essentia host/SPI migration record (31 October 2026)

## 31 October update: upstream scan lifecycle and fresh full-catalog fingerprint

- Confirmed from upstream [Lyrion scanner](https://github.com/LMS-Community/slimserver/blob/public/9.2/scanner.pl)
  that `lastscan` is not an immutable generation: timestamp changes are
  conditional, scan commits can occur incrementally, and `rescan done`
  / `library changed` are notifications. Do not derive a trusted shared
  scanner/host generation merely from them.
- In [lms-guidance-essentia Draft PR #1](https://github.com/chrober/lms-guidance-essentia/pull/1)
  `CatalogFingerprint.pm` now computes a bounded deterministic SHA-256 of
  **all eligible** Bliss `TracksV2.File` rows plus caller-declared host
  root IDs/canonical paths under a readonly pinned SQLite snapshot.
- A new independent readonly WAL transaction is used for freshness
  checks. Optional offline `catalog_roots` binding into the SHA-audited
  resource bundle rechecks before SPI prepare and can recheck after score.
  The real native SPI remains unchanged; `signals=[]`.
- [CI PASS: 136 Perl + 20 actual native JSONL process assertions]
  (https://github.com/chrober/lms-guidance-essentia/actions/runs/41200038531).
  Native fixture deliberately changes Bliss after scoring and confirms
  the older catalog fingerprint is rejected.
- **Important:** A fingerprint is not an authenticated Lyrion scan
  epoch, roots are still caller-declared, and the scanner has no
  durable root-qualified analysis receipt. The producer/host must
  close those gaps before activating the provider. No changes to
  BlissMixerLab, its closed PR #3, or the public SPI.

## 31 October follow-up: per-file content provenance without Lab changes

- [Lab PR #3](https://github.com/chrober/lms-blissmixer-lab/pull/3)
  is now **closed without merge**. `main` is unchanged. Earlier Lab
  code/proofs in this document remain historical only.
- [Lyrion provider Draft PR #1](https://github.com/chrober/lms-guidance-essentia/pull/1)
  now contains a normal SPI-v2 provider discovery facade that
  **always reports unavailable** until genuine host/scanner provenance
  is established. All Essentia-specific work remains here, not in Lab.
- New `SourceProvenance.pm` attests an offline seed plus 2–50 candidates
  by streaming SHA-256 over the actual file bytes and comparing against
  existing scanner SQLite-v3 `feature_tracks.audio_sha256`, exact
  `TracksV2.File`, model key and scan-state file size. With multiple
  configured music roots, each path must have one unique owning root,
  and all relative-key collisions are rejected.
- The content-audited identities and <=4 MiB selected-feature projection
  are passed in the **unchanged** native `bliss-playlist-guidance-spi`
  v2 artifact/resource shape. The existing Rust provider still emits
  **only `signals=[]`** and has not been connected to running LMS.
- [Real native process CI PASS, 113 Perl + 15 native assertions]
  (https://github.com/chrober/lms-guidance-essentia/actions/runs/41197901541):
  two physical roots and all current file bytes are checked before
  `describe -> prepare -> score -> close` on a synthetic fixture.
- **Do not conflate per-track content proof with common catalogue
  generation.** The current scanner has no host generation or root-map
  attestation, and its source SHA is computed after decoding without
  a before/after source stability proof. That scanner race and portable
  generation provenance remain explicit blockers. Full-file hashing
  would also exceed live-mixer latency budgets on many systems.

See [specific offline proof and limitations]
(https://github.com/chrober/lms-guidance-essentia/blob/feat/essentia-guidance-integration-design/docs/audio-content-provenance-20261031.md).

---

## AUTHORITATIVE ARCHITECTURE DECISION: SPI-only integration

The previous Lab-local Essentia identity, bounded snapshot and direct
native `EssentiaShadowProbe` integration was **removed** from the
[Lab Draft PR #3](https://github.com/chrober/lms-blissmixer-lab/pull/3)
after review: **BlissMixerLab must be completely provider-neutral**.
The new Lab draft contains only a generic, manually opted-in passive
observation helper implemented on top of the already existing native
Guidance SPI callbacks. It is not connected to live DSTM or playback.

The reusable exact-key verifier and <=4 MiB bounded SQLite-v3 projection
were relocated to the separate
[Lyrion Essentia provider Draft PR #1](https://github.com/chrober/lms-guidance-essentia/pull/1).
That plugin branch is still **not installable or registered**. The native
[Essentia SPI v2 provider Draft PR #1](https://github.com/chrober/bliss-guidance-essentia/pull/1)
is unchanged at the wire-contract level and continues to return `signals=[]`.
Only the existing SPI `describe / prepare / score / close` mechanism may
invoke it; no provider-specific direct subprocess path belongs in Lab.

Host/source-generation equality, multiple-root provenance and exact
audio-file identity are **not yet proven**; matching relative keys and
separately frozen databases are insufficient. The current provider plugin
must therefore remain inactive until trusted evidence and real-host
fail-closed tests are implemented. The generic Lab does not own these
provider-specific validators.

Verified CI:
- [Provider helper tests](https://github.com/chrober/lms-guidance-essentia/actions) are green.
- Generic Lab SPI tests are in [Lab Draft PR #3](https://github.com/chrober/lms-blissmixer-lab/pull/3).
- [Provider-owned SPI plan](https://github.com/chrober/lms-guidance-essentia/blob/feat/essentia-guidance-integration-design/docs/provider-owned-spi-shadow-20261031.md).

## Superseded historical research notes

The following chronology documents what **was** tested in the abandoned
Lab-local proof. It is retained for reproducibility only and must not
be mistaken for currently present Lab modules or active integration.

---
# Lyrion Essentia P1: verified host identity and native frozen-shadow first slice (31 October 2026)

## P1.5 update: scalable bounded native shadow probe (31 October 2026)

The isolated Lab Draft PR #3 has moved from *full SQLite online backup*
to a **read-only, per-cohort feature projection**:

- `EssentiaBoundedSnapshot.pm` opens each source with actual SQLite
  `OPEN_READONLY` and pins separate read transactions (including WAL).
- Exact Bliss/Essentia identity validation still runs against the original
  sources; only one seed, 2–50 admitted candidates, and one requested
  model are exported to a private sealed SQLite-v3 file (max 4 MiB).
- The native SPI v2 `describe` / `prepare` / `score` / `close` flow is
  unchanged. All `signals=[]`; no run-time Lab integration or player effect.
- Concurrent WAL changes cannot alter already pinned feature rows. Missing
  keys, invalid model fingerprints, non-BLOB feature data and incomplete
  cohorts fail neutrally.
- New [Lab bounded-shadow and provenance contract]
  (https://github.com/chrober/lms-blissmixer-lab/blob/feat/essentia-exact-identity-proof/docs/essentia-host-provenance-and-bounded-shadow-20261031.md).
- [Initial bounded native CI](https://github.com/chrober/lms-blissmixer-lab/actions/runs/41189833771)
  PASS: 69 assertions across four Perl suites and actual pinned Rust provider.
  [General CI](https://github.com/chrober/lms-blissmixer-lab/actions/runs/41189833767)
  PASS: 329 regression assertions. Later hardening CI must also pass.

**P2 remains blocked** on independently verifiable host-owned scan-generation
attestation, provenance for multiple media roots and physical file identity,
plus end-to-end real host smoke/performance measurements. The SQLite
transactions are individually consistent, **not an atomic cross-database
generation**. V3 exact relative file keys alone cannot disambiguate
same-named files from distinct roots. Existing scanner and Bliss databases
must not be silently modified to fabricate a generation witness.

All information below describes the historical earlier P1 full-copy proof;
its SQLite online-backup implementation has been replaced.

---

## Verified implementation

- Main implementation: [lms-blissmixer-lab Draft PR #3](https://github.com/chrober/lms-blissmixer-lab/pull/3), branch feat/essentia-exact-identity-proof, current verified tip 2bcd8bcbcda16b0b964eee077ec63908cfd1d0ea.
- Canonical offline feature writer remains in essentia-analyser; independent geometry and read-only feature decoder remain in essentia-similarity. No repository merge or scanner migration.
- Native JSONL process comes from bliss-guidance-essentia Draft PR #1, pinned revision de72433d9c690e1aa46e973bbcca63691e959df8. The Lyrion install/setting project lms-guidance-essentia remains separate and documentation-only.
- Host-side EssentiaExactIdentity.pm verifies exact binary Bliss TracksV2.File and Essentia SQLite-v3 feature_tracks.track_file keys, one anchor and complete 2–50 already-admitted candidates, then writes bounded SHA256 job-bound essentia-exact-track-keys-v1 metadata.
- Explicit opt-in only EssentiaShadowProbe.pm opens both source DBs with actual SQLITE_OPEN_READONLY, makes private WAL-aware SQLite Online Backup snapshots, then verifies and provides the frozen sidecar to the native provider. It runs real describe/prepare/score/close requests with verified manifest and response semantics.
- All outputs remain anonymous status/aggregate only; empty provider signals are enforced as a safety gate. Original SQLite bytes, playback, queues, route plans and Bliss ranking stay unchanged.

## Tested evidence

- [Native integration GitHub Actions 41184700040](https://github.com/chrober/lms-blissmixer-lab/actions/runs/41184700040): SUCCESS on 31 October 2026, includes actual Cargobuilt Rust provider, true temporary SQLite files, strict BLOB Float32LE model head, raw source vs frozen copy equivalence, model mismatch fallback, and complete-cohort safety.
- [Regular CI 41184700041](https://github.com/chrober/lms-blissmixer-lab/actions/runs/41184700041): SUCCESS, retained old Lab Perl/Python regressions. Full P1 branch CI passes. Experimental shadow opt-in only literal scalar 1; string false does not enable.
- Technical integration details, failure contracts and synthetic fixtures are maintained at [Lab P1 implementation notes](https://github.com/chrober/lms-blissmixer-lab/blob/feat/essentia-exact-identity-proof/docs/essentia-exact-identity-proof-20261031.md).

## Interpretation and explicit no-go

This is an isolated, manually called **research P1 proof**, not a live Lab SPI host integration, supported Lyrion plugin, production General Metric or user-visible Shadow UI. Native provider still emits zero active signals. No routing/playback changes have been shipped.

SQLite online backup captures each source independently, **not one atomic common snapshot** across Bliss and Essentia generations. Distinct physical media roots remain rejected without a trustworthy root/source-generation identity contract. The full-database temporary copy is bounded to 256 MiB per source and is **not** a scalable Raspberry Pi or large-library runtime approach. Native package licensing, source-feature parity, model rights, actual general/personal musical quality and low-power timings remain open.

## Recommended next experiment

Introduce a read-only host-controlled source-generation manifest and lightweight, bounded, zero-playback-change candidate snapshot interface. Confirm exact root identity, rescan consistency, one explicit seed and entire admitted pool. Then evaluate a gated Lab Shadow report that records only anonymous coverage, fallback rate, p95/p99 latency and ranking-delta aggregates. Only after external musical validation may an actual ranking influence be proposed. WP1, WP2, WP3 and FMA TEST embargo remain unaffected.
