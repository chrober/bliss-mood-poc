# Offline Mood SQLite architecture (schema v2)

## Goal

Mirror the proven *offline analysis, online retrieval* workflow of [Bliss Analyser](https://github.com/CDrummond/bliss-analyser), while keeping upstream `bliss.db` entirely unchanged.

1. Analyse a music file on any adequately powerful machine.
2. Persist scores and exact model/preprocessing provenance in `mood.db` (SQLite).
3. Transfer the complete portable SQLite file to the Raspberry Pi / Lyrion host.
4. At playlist generation time, load/lookup cached data only. **No ONNX Runtime, FFmpeg or neural model files are required during mix creation.** The Pi can optionally host the native analyzer for post-scan updates.

**Important:** Current classifier / Mel preprocessing implementation is still a prototype, not numerically verified against Essentia. All stored rows retain `validated_against_essentia = 0` until actual reference validation has been performed. Host consumers MUST default to ignoring unvalidated rows.

## Existing Bliss key contract

Confirmed from the upstream source:

- `bliss.db` has `TracksV2.File` (exact song path) and `TracksV2.rowid`.
- `bliss-mixer` resolves a song ID using `SELECT rowid FROM TracksV2 WHERE File=:path`.
- Upstream Lyrion stores `bliss.db` in the LMS preferences directory.

**Never persist `TracksV2.rowid` as a cross-database identity**: reimports may change rowids. The external Mood database uses `track_file` matching the exact `TracksV2.File` value. Matching must be byte-for-byte rather than a heuristic by artist/title.

Example external analysis:

- Filesystem path on analysis machine: `D:\\Music\\Rock\\Song.flac`
- Corresponding `TracksV2.File` on Lyrion: `/mnt/music/Rock/Song.flac`
- Proposed command:

```powershell
bliss-mood analyze "D:\Music\Rock\Song.flac" --models-dir models --db mood.db --track-key "/mnt/music/Rock/Song.flac" --json
```

The supplied track key must match Bliss exactly. This explicit `--track-key` is deliberate; silent path rewriting causes false joins. The implemented `scan` command provides explicit source/library root mappings, refusing ambiguous, duplicated, or unmatched paths.

## Storage schema

SQLite database `mood.db`, `PRAGMA user_version = 2` (v1 migrates without deleting score rows):

```sql
CREATE TABLE mood_models (
  model_key TEXT PRIMARY KEY,                   -- SHA-256 identity of provenance + ordered label names
  embedding_model TEXT NOT NULL,
  classification_model TEXT NOT NULL,
  models_sha256_json TEXT NOT NULL,
  preprocessing_version TEXT NOT NULL,
  aggregation TEXT NOT NULL,
  classes_json TEXT NOT NULL,                   -- ordered labels for score vector
  validated_against_essentia INTEGER NOT NULL CHECK (... IN (0,1))
);
CREATE TABLE mood_tracks (
  track_file TEXT PRIMARY KEY,                  -- exactly TracksV2.File
  audio_sha256 TEXT NOT NULL,
  model_key TEXT NOT NULL REFERENCES mood_models(model_key),
  scores_f32_le BLOB NOT NULL,                  -- 56 IEEE-754 floats = 224 bytes
  patches_analyzed INTEGER NOT NULL,
  analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE mood_track_state (
  track_file TEXT PRIMARY KEY REFERENCES mood_tracks(track_file),
  file_size INTEGER NOT NULL,
  modified_ns INTEGER NOT NULL,
  model_key TEXT NOT NULL
);
```

This avoids duplicating names/metadata and a 56-key JSON object in every song row. The score vector is associated with explicit label order and exact model identity. Prototypes may contain more than one model in the model catalog, but an individual track row always has one current analysis. A model upgrade replaces the affected track's row atomically.

The per-track scan snapshot is updated in the same SQLite transaction as its successful Mood scores. On subsequent scans, a matching model key, file size, and modification time avoid recomputing an unchanged song. A standalone single-file reanalysis invalidates its previous scan snapshot. All scores must be finite and in [0,1] and have exactly 56 named labels. The DB reports and comparison always explicitly indicate if the reference validation flag is false.

## Transfer and lifecycle

- Analyse the master library on a workstation/other server; do not read/write audio tags.
- Incremental updates use file identity and model/proprocessing hashes (future batch feature). An edited audio file or updated model is re-analysed. Deleted songs can be pruned **only** by an explicit maintenance action.
- Verify the completed DB using `PRAGMA integrity_check`, check `bliss.db` coverage, transfer to a *staging filename*, then atomically replace active `mood.db` on the server (ideally without concurrent readers or using a reopen).
- Do not copy a live WAL-mode database without an SQLite backup/snapshot.
- Host loading should compare expected schema/model and reject stale/unvalidated scores; missing tracks fall back to pure Bliss similarity.
- Normal mixes should not query ONNX or write `bliss.db`.

## Experiment and integration sequence

1. **Now:** SQLite storage for a single analyzed file, read-only coverage check, unit tests.
2. **Before rollout:** Correct the ESSENTIA preprocessing, run model end-to-end, compare reference vectors and scores.
3. Add batch scanning, configurable root mappings, incremental reanalysis and failures/progress.
4. Add external DB loading and configurable score/rank fusion in a *separate experimental provider / Lab*; preserve standard Bliss Mixer behavior.
5. Benchmark the on-demand retrieval RAM and latency on a Pi 4B. Optional Pi-side analysis only after compatible ARM64 builds.

Existing references: [BlissMixerLab](https://github.com/chrober/lms-blissmixer-lab), [Better Call Bliss](https://github.com/chrober/lms-better-call-bliss), [similarity-design](https://chrober.github.io/bliss-similarity-design/).

## Current hybrid implementation

Use `bliss-mood scan --bliss-db ... --db ... --models-dir ...` for the offline batch and on-Pi incremental analysis. The same native binary handles both. Optional `--library-root` and `--source-root` map the Lyrion file identity to the analysis computer's media folder. `--dry-run` opens the current Mood DB read-only (and does not create it), `--max-new N` caps analyzed songs, and `--threads 1` limits ONNX intra-op parallelism. All model sessions are initialized once per batch, on the first pending song. See [hybrid design](lyrion-hybrid-analysis.md).

Automatic *Lyrion* post-scan triggering, native binary packaging for piCorePlayer and numerical comparison to Essentia remain outstanding. Do not deploy unvalidated scores as production mix signals.
