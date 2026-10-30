#!/usr/bin/env python3
"""WP3-R5: select a NEW, metadata-disjoint, Bliss-available cohort, NO audio scans.

A private research manifest, NOT a human similarity evaluation and NOT a
teacher-model validation. Exact Lyrion IDs/URLMD5, shared ARTIST/TRACKARTIST
credits, LMS album IDs and MusicBrainz recording IDs are checked. Missing
recording MBID candidates are excluded, never assumed independent.
No Essentia features/teacher predictions are read for the NEW candidates.
No user labels, audio files, network service calls, or writes to source DBs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing, ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys

from audit_bliss_essentia_join import open_bliss, BLISS_COLUMNS
from derive_lyrion_research_groups import SCHEMA_IDENTITY, _MBID, _required_columns

SCHEMA = "wp3-independent-cohort-plan-v1"
MIN_COUNT, MAX_COUNT = 24, 1000
DEFAULT_COUNT = 240
SEED = 20261030
OLD_SCHEMA = "lyrion-wp3-research-snapshot-v1"
GROUP_FIELDS = ("artist_group", "album_group", "recording_group")


def _db(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("Required existing SQLite database is missing")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def _valid(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "\0" not in value


def _quartile(value: float, thresholds: tuple[float, float, float]) -> int:
    return sum(value > threshold for threshold in thresholds)


def _thresholds(values: list[float]) -> tuple[float, float, float]:
    x = sorted(values)
    return x[len(x)//4], x[len(x)//2], x[(3*len(x))//4]


def _load_bliss_valid(db: sqlite3.Connection) -> dict[str, tuple[float, float]]:
    """One sequential read, no N SQL lookups on possibly unindexed TracksV2.File."""
    fields = ", ".join('"' + x + '"' for x in BLISS_COLUMNS)
    rows = db.execute('SELECT "File",' + fields + ' FROM TracksV2')
    valid = {}
    repeated = set()
    for key, *values in rows:
        if not _valid(key):
            continue
        if key in valid:
            repeated.add(key)
            continue
        if (len(values) != 23 or any(type(v) not in (float, int)
              or not math.isfinite(v) for v in values)):
            continue
        valid[key] = (float(values[0]), float(values[2]))
    for key in repeated:
        valid.pop(key, None)
    return valid


def plan(bliss: Path, snapshot: Path, library: Path,
         previous: Path, *, count: int = DEFAULT_COUNT,
         seed: int = SEED) -> tuple[dict, dict]:
    if type(count) is not int or not MIN_COUNT <= count <= MAX_COUNT:
        raise ValueError("New cohort size out of allowed bounds")
    if type(seed) is not int or seed <= 0:
        raise ValueError("Seed must be a fixed positive integer")
    if len({str(p.resolve()).casefold() for p in (bliss,snapshot,library,previous)}) != 4:
        raise ValueError("Four separate source databases are required")

    with ExitStack() as stack:
        b = stack.enter_context(closing(open_bliss(bliss)))
        sn = stack.enter_context(closing(_db(snapshot)))
        lm = stack.enter_context(closing(_db(library)))
        old = stack.enter_context(closing(_db(previous)))

        _required_columns(sn, "metadata", {"key","value"})
        _required_columns(sn, "track_identity",
            {"database_file","lms_track_id","lms_urlmd5","recording_mbid"})
        _required_columns(sn, "track_artist_identity",
            {"database_file","role","canonical_key"})
        _required_columns(lm, "tracks",
            {"id","urlmd5","musicbrainz_id","album","remote","audio"})
        _required_columns(lm, "albums", {"id"})
        _required_columns(old, "metadata", {"key","value"})
        _required_columns(old, "paired_tracks",
            {"track_key","artist_group","album_group","recording_group"})
        metadata = dict(sn.execute("SELECT key,value FROM metadata"))
        if (metadata.get("schema_identity") != SCHEMA_IDENTITY
                or not str(metadata.get("lms_scan_time","")).isdigit()
                or int(metadata["lms_scan_time"]) <= 0
                or re.fullmatch("[0-9a-fA-F]{64}",metadata.get("media_roots_identity","")) is None):
            raise ValueError("Unsupported or unverified snapshot source identity")
        previous_meta = dict(old.execute("SELECT key,value FROM metadata"))
        if (previous_meta.get("schema") != OLD_SCHEMA
                or previous_meta.get("group_readiness") != "READY"):
            raise ValueError("Prior cohort must be source-verified and grouped")
        old_keys = set()
        for key, artist, album, recording in old.execute(
                "SELECT track_key,artist_group,album_group,recording_group FROM paired_tracks"):
            if not _valid(key) or key in old_keys or not all(_valid(x) for x in
                    (artist,album,recording)):
                raise ValueError("Prior grouped cohort provenance is incomplete")
            old_keys.add(key)
        if len(old_keys) < 24:
            raise ValueError("Not enough established prior cohort identities")

        # Do not publish any of these private artist/recording values.
        index = {}
        duplicated = set()
        for key, tid, md5, rec in sn.execute(
                "SELECT database_file,lms_track_id,lms_urlmd5,recording_mbid FROM track_identity"):
            if not _valid(key):
                continue
            if key in index:
                duplicated.add(key)
            index[key] = (tid,md5,rec)
        for key in duplicated:
            index.pop(key, None)
        artist_keys = defaultdict(set)
        for key, role, identity in sn.execute(
                "SELECT database_file,role,canonical_key FROM track_artist_identity"):
            if role in ("ARTIST","TRACKARTIST") and _valid(key) and _valid(identity):
                artist_keys[key].add(identity)
        album_ids = {row[0] for row in lm.execute("SELECT id FROM albums")}
        tracks = {row[0]:row[1:] for row in lm.execute(
            "SELECT id,urlmd5,musicbrainz_id,album,remote,audio FROM tracks")}
        bliss_eligible = _load_bliss_valid(b)
        # Fail closed when any of the OLD 100 cannot be verified in the
        # current copied sources; then "disjoint" cannot be asserted.
        previous_artists, previous_albums, previous_recordings = set(), set(), set()
        for key in old_keys:
            if key not in index or key not in artist_keys:
                raise ValueError("Old cohort missing exact Lyrion snapshot identity")
            tid, md5, recorded = index[key]
            if type(tid) is not int or not _valid(md5) or tid not in tracks:
                raise ValueError("Old cohort track identity invalid")
            url, rec, album, remote, audio = tracks[tid]
            if url != md5 or remote != 0 or audio != 1 or album not in album_ids:
                raise ValueError("Old cohort identity changed across sources")
            if recorded is not None and recorded != rec:
                raise ValueError("Old cohort recording identity changed")
            previous_artists.update(artist_keys[key])
            previous_albums.add(album)
            if _valid(rec) and _MBID.fullmatch(rec.strip().lower()):
                previous_recordings.add(rec.strip().lower())

        counts = Counter()
        options = []
        for key, (tid,md5,recorded) in index.items():
            counts["snapshot_rows_with_unique_keys"] += 1
            if key in old_keys:
                counts["previous_songs_skipped"] += 1
                continue
            if key not in bliss_eligible:
                counts["no_unique_valid_bliss23"] += 1
                continue
            if type(tid) is not int or not _valid(md5) or tid not in tracks:
                counts["lms_identity_missing"] += 1
                continue
            url, rec, album, remote, audio = tracks[tid]
            if (url != md5 or remote != 0 or audio != 1
                    or (recorded is not None and recorded != rec)):
                counts["lms_identity_mismatch_or_non_audio"] += 1
                continue
            if album not in album_ids:
                counts["album_unverified"] += 1
                continue
            artists = artist_keys.get(key, set())
            if not artists:
                counts["artist_unverified"] += 1
                continue
            mbid = rec.strip().lower() if _valid(rec) else ""
            if not _MBID.fullmatch(mbid):
                counts["recording_mbid_unverified"] += 1
                continue
            if (artists & previous_artists or album in previous_albums
                    or mbid in previous_recordings):
                counts["prior_cohort_identity_overlap"] += 1
                continue
            tempo, brightness = bliss_eligible[key]
            options.append({
                "track_key": key, "lms_track_id": tid,
                "artists": tuple(sorted(artists)),
                "album":album, "recording":mbid,
                "tempo":tempo,"brightness":brightness,
            })
        if len(options) < count:
            raise ValueError("Insufficient verifiably independent Bliss-ready candidates")
        tempo_q = _thresholds([r["tempo"] for r in options])
        bright_q = _thresholds([r["brightness"] for r in options])

        bins = defaultdict(list)
        for item in options:
            cell = "%d%d" % (_quartile(item["tempo"],tempo_q),
                             _quartile(item["brightness"],bright_q))
            bins[cell].append(item)
        # All decisions are deterministic from seed + song key, NOT Essentia
        # teacher predictions, ratings, or data from future evaluation.
        for cell in bins:
            bins[cell].sort(key=lambda x: (
                hashlib.sha256((str(seed)+"|"+x["track_key"]).encode()).hexdigest(),
                x["track_key"]))
        slots = sorted(bins)
        offsets = {cell:0 for cell in slots}
        chosen = []
        used_artist,used_album,used_rec=set(),set(),set()
        while len(chosen) < count:
            progress = False
            for cell in slots:
                while offsets[cell] < len(bins[cell]):
                    row = bins[cell][offsets[cell]]
                    offsets[cell] += 1
                    if (set(row["artists"]) & used_artist or
                            row["album"] in used_album or
                            row["recording"] in used_rec):
                        continue
                    chosen.append((cell,row))
                    used_artist.update(row["artists"])
                    used_album.add(row["album"])
                    used_rec.add(row["recording"])
                    progress = True
                    break
                if len(chosen) == count:
                    break
            if not progress:
                raise ValueError("Insufficient mutually artist-disjoint future candidates")
        # Full private manifest is required to reproduce a future new
        # cohort; private identities must never leave the operator's PC.
        manifest = {
            "schema":SCHEMA,
            "status":"PRIVATE_CANDIDATE_PROPOSAL_NO_AUDIO_OR_HUMAN_VALIDATION",
            "seed":seed,
            "requested_new_songs":count,
            "prior_grouped_songs_excluded":len(old_keys),
            "selection":"seeded_SHA256_round_robin_Bliss_tempo_centroid_quartiles",
            "all_exact_source_mappings_checked":True,
            "selected_songs":[{
                "track_file":x["track_key"], "lms_track_id":x["lms_track_id"],
                "artist_keys":list(x["artists"]),
                "lms_album_id":x["album"],
                "recording_mbid":x["recording"],
                "bliss_sampling_stratum":cell,
            } for cell,x in chosen],
            "warnings":[
                "These are only candidates, not new processed Essentia songs.",
                "Current live LMS scan and audio-byte provenance remain uncertified.",
                "Unknown recording IDs are excluded, but erroneous MBIDs may hide duplicates.",
                "The first 100 previously explored tracks are not untouched controls.",
                "Bliss tempo/centroid bins are diversity proxies, not genre labels.",
                "No human similarity judgments, model parameters, or metric improvements.",
            ],
        }
        aggregate = {
            "schema":SCHEMA,
            "status":"NEW_SOURCE_DISJOINT_BLISS_COHORT_PROPOSED_NOT_EVALUATED",
            "new_songs":len(chosen),
            "prior_research_songs_excluded":len(old_keys),
            "mutually_nonoverlapping_artist_album_recording_identities":True,
            "unverified_or_unknown_recording_candidates_excluded":True,
            "all_candidates_have_unique_valid_Bliss23":True,
            "selection_strata":dict(sorted(Counter(cell for cell,_ in chosen).items())),
            "counts":dict(sorted(counts.items())),
            "essentia_on_new_songs_available":False,
            "human_similarity_evaluated":False,
            "previous_train_group_leakage_certified_absent_against_current_sources":True,
            "new_source_model_training_overlap_independently_certified":False,
            "current_live_LMS_scan_freshness_certified":False,
            "source_song_identifiers_or_vectors_in_stdout":False,
        }
        return manifest,aggregate


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bliss-db",required=True,type=Path)
    p.add_argument("--repeat-identity-db",required=True,type=Path)
    p.add_argument("--lyrion-library-db",required=True,type=Path)
    p.add_argument("--prior-research-db",required=True,type=Path)
    p.add_argument("--count",type=int,default=DEFAULT_COUNT)
    p.add_argument("--seed",type=int,default=SEED)
    p.add_argument("--out-private",type=Path,
                   help="New private JSON, required except for --preflight")
    p.add_argument("--preflight",action="store_true",
                   help="Only anonymized counts, no file output")
    a=p.parse_args()
    try:
        if not a.preflight:
            if a.out_private is None or a.out_private.exists() or a.out_private.is_symlink():
                raise ValueError("Require a NEW private manifest path")
        manifest, aggregate=plan(a.bliss_db,a.repeat_identity_db,a.lyrion_library_db,
                                 a.prior_research_db,count=a.count,seed=a.seed)
        if not a.preflight:
            with a.out_private.open("x",encoding="utf-8") as f:
                json.dump(manifest,f,indent=2,ensure_ascii=False,allow_nan=False)
                f.write("\n")
        print(json.dumps(aggregate,indent=2,ensure_ascii=False,allow_nan=False))
    except (ValueError,KeyError,TypeError,OverflowError,OSError,sqlite3.Error):
        p.exit(2,"Independent-cohort planning BLOCKED: required read-only identities "
                  "or independent candidates unavailable; no musical quality certified\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
