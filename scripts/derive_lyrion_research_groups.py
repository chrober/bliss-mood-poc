#!/usr/bin/env python3
"""WP3-R4: derive private research groups from EXISTING Lyrion/Lab databases.

Uses exact file key -> BlissMixerLab artist-repeat identity snapshot ->
Lyrion library tracks.id/album. No filename-derived artist/album guesses.
Missing recording MBID is CONSERVATIVELY put in one shared unknown group,
rather than asserting unrelated recordings are independent. No music decoding,
LMS calls, source writes or feature export. PRIVATE metadata must stay local.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import re
from pathlib import Path
import sqlite3
import sys

from audit_bliss_essentia_join import (
    open_bliss, bliss_vector, compatible_essentia_provenance,
)
import evaluate_similarity as ev
from research_grouped_split import grouped_partition

SCHEMA_IDENTITY = "lyrion-track-identities-v1"
UNKNOWN_RECORDING = "unknown-recording-identity-all-shared"
_MBID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
MIN_READY = 24
MAX_READY = 300


def _open_existing(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("Missing existing read-only source database")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def _required_columns(conn: sqlite3.Connection, table: str, names: set[str]) -> None:
    # Table/column names are constants, never user SQL.
    columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if not names <= columns:
        raise ValueError("Lyrion snapshot or library schema does not match expected version")


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "\0" not in value


def _opaque_group_components(keys: list[str], artists: dict[str, tuple[str, ...]]) -> dict[str, str]:
    # Any shared artist role connects songs. Unlike a concatenated artist
    # credit string, this does not accidentally separate collaborations.
    parent = {k: k for k in keys}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def merge(a,b):
        ra,rb = root(a),root(b)
        if ra != rb:
            parent[max(ra,rb)] = min(ra,rb)
    by_artist = {}
    for key in keys:
        for identity in artists[key]:
            if identity in by_artist:
                merge(by_artist[identity], key)
            else:
                by_artist[identity] = key
    # Root strings are raw song keys, but these are output only to an
    # explicitly private local JSON file and never returned by the CLI.
    return {key: "artist-connected:" + root(key) for key in keys}


def generate_private_groups(
    bliss_db: Path, feature_db: Path, snapshot_db: Path, lyrion_db: Path,
    *, seed: int = 20261029, limit: int = 100,
    preflight: bool = False,
) -> tuple[dict, dict]:
    """Return PRIVATE key->groups plus public-safe aggregate; do not print map."""
    if type(limit) is not int or not MIN_READY <= limit <= MAX_READY:
        raise ValueError("Group-study sample must be in 24..300")
    if type(seed) is not int:
        raise ValueError("Deterministic group seed must be an integer")
    with closing(open_bliss(bliss_db)) as bliss:
        with closing(ev.open_database(feature_db)) as sidecar:
            with closing(_open_existing(snapshot_db)) as snapshot:
                with closing(_open_existing(lyrion_db)) as lyrion:
                    _required_columns(snapshot,"metadata",{"key","value"})
                    _required_columns(snapshot,"track_identity",{
                        "database_file","lms_track_id","lms_urlmd5","recording_mbid",
                    })
                    _required_columns(snapshot,"track_artist_identity",{
                        "database_file","role","canonical_key",
                    })
                    _required_columns(lyrion,"tracks",{
                        "id","urlmd5","musicbrainz_id","album","remote","audio",
                    })
                    _required_columns(lyrion,"albums",{"id"})
                    schema = snapshot.execute(
                        "SELECT value FROM metadata WHERE key='schema_identity'"
                    ).fetchone()
                    if schema is None or schema[0] != SCHEMA_IDENTITY:
                        raise ValueError("Unsupported artist-repeat snapshot provenance")
                    cohorts = {head:ev._catalog(sidecar,head,experimental=True)
                               for head in ("genre","moodtheme")}
                    if len({x["preprocessing_version"] for x in cohorts.values()}) != 1:
                        raise ValueError("Inconsistent existing classifier preprocessing")
                    selected = ev.load_sample(sidecar,cohorts,limit,seed)
                    result = {}
                    artists = {}
                    counts = {
                        "eligible_essentia_head_population":selected["valid_total"],
                        "selected_head_pairs":selected["sample_size"],
                        "excluded_bad_essentia_provenance":0,
                        "excluded_missing_invalid_bliss":0,
                        "missing_or_unverified_lms_identity":0,
                        "missing_artist_credit":0,
                        "missing_album_identity":0,
                        "recording_mbid_unavailable":0,
                        "paired_tracks_with_verified_lms_artist_album":0,
                    }
                    for key in selected["tracks"]:
                        if compatible_essentia_provenance(sidecar,key,cohorts) is None:
                            counts["excluded_bad_essentia_provenance"] += 1
                            continue
                        status, _ = bliss_vector(bliss,key)
                        if status != "valid":
                            counts["excluded_missing_invalid_bliss"] += 1
                            continue
                        hits = snapshot.execute(
                            "SELECT lms_track_id,lms_urlmd5,recording_mbid "
                            "FROM track_identity WHERE database_file=? COLLATE BINARY LIMIT 2",
                            (key,),
                        ).fetchall()
                        if len(hits)!=1:
                            counts["missing_or_unverified_lms_identity"] += 1
                            continue
                        track_id,url_md5,recording_id = hits[0]
                        if (type(track_id) is not int or not _nonempty(url_md5)):
                            counts["missing_or_unverified_lms_identity"] += 1
                            continue
                        track = lyrion.execute(
                            "SELECT id,urlmd5,musicbrainz_id,album,remote,audio "
                            "FROM tracks WHERE id=? LIMIT 2",(track_id,)
                        ).fetchall()
                        if len(track)!=1:
                            counts["missing_or_unverified_lms_identity"] += 1
                            continue
                        lid,lmd5,lrecord,album_id,remote,audio = track[0]
                        # Snapshot might be stale after a Lyrion rescan. Compare
                        # both independent IDs and their url checksum exactly.
                        if (lid != track_id or lmd5 != url_md5 or remote != 0 or audio != 1
                                or (recording_id is not None and
                                    recording_id != lrecord)):
                            counts["missing_or_unverified_lms_identity"] += 1
                            continue
                        if type(album_id) is not int or lyrion.execute(
                            "SELECT id FROM albums WHERE id=?",(album_id,)
                        ).fetchone() is None:
                            counts["missing_album_identity"] += 1
                            continue
                        credited = tuple(sorted({
                            row[0] for row in snapshot.execute(
                                "SELECT canonical_key FROM track_artist_identity "
                                "WHERE database_file=? COLLATE BINARY "
                                "AND role IN ('ARTIST','TRACKARTIST')",
                                (key,)
                            ) if _nonempty(row[0])
                        }))
                        if not credited:
                            counts["missing_artist_credit"] += 1
                            continue
                        artists[key] = credited
                        mbid = lrecord.strip().lower() if _nonempty(lrecord) else ""
                        if not _MBID.fullmatch(mbid):
                            counts["recording_mbid_unavailable"] += 1
                        result[key] = {
                            "album_group":"lms-album-id:"+str(album_id),
                            "recording_group":("musicbrainz-recording:"+mbid
                                               if _MBID.fullmatch(mbid) else UNKNOWN_RECORDING),
                        }
                    counts["paired_tracks_with_verified_lms_artist_album"]=len(result)
                    # Audit mode emits reason codes/counts without writing a
                    # source-derived private groups file. Default strict mode
                    # retains its original fail-closed behavior.
                    failure = None
                    if len(result)<MIN_READY:
                        failure = "TOO_FEW_VERIFIED_PAIRED_SONGS"
                    elif (counts["missing_or_unverified_lms_identity"]
                            or counts["missing_artist_credit"]
                            or counts["missing_album_identity"]):
                        failure = "INCOMPLETE_LYRION_TRACK_ARTIST_ALBUM_IDENTITY"
                    part = None
                    if result:
                        connected = _opaque_group_components(sorted(result),artists)
                        for key in result:
                            result[key]["artist_group"]=connected[key]
                        rows=[{"track_id":key,**meta} for key,meta in result.items()]
                        try:
                            part=grouped_partition(rows,seed=seed,test_fraction=0.25)
                        except ValueError:
                            if failure is None:
                                failure = "NO_GROUP_DISJOINT_HOLDOUT"
                        if part is not None and min(len(part.train),len(part.holdout))<12:
                            if failure is None:
                                failure = "GROUP_DISJOINT_HOLDOUT_TOO_SMALL"
                    if failure is not None and not preflight:
                        raise ValueError("Incomplete Lyrion grouping or independent holdout")
                    aggregate={
                        "schema":"lyrion_snapshot_exact_group_provenance_v1",
                        "status":("SOURCE_GROUPING_READY_PRIVATE_NO_AUDIO_SCANS"
                                  if failure is None else "SOURCE_GROUPING_BLOCKED_NO_OUTPUT"),
                        "ready_for_grouped_study":failure is None,
                        "blocking_reason_code":failure,
                        "sample_seed":seed,
                        "sample_limit":limit,
                        "counts":counts,
                        "artist_album_recording_connected_components":(
                            part.connected_groups if part is not None else 0),
                        "train_songs":len(part.train) if part is not None else 0,
                        "holdout_songs":len(part.holdout) if part is not None else 0,
                        "recording_mbid_missing_all_share_one_conservative_group":True,
                        "snapshot_lms_id_urlmd5_checked":True,
                        "snapshot_schema_identity_checked":True,
                        "data_sources_opened_query_only":True,
                        "source_audio_identity_independently_certified":False,
                        "teacher_training_overlap_ruled_out":False,
                        "private_grouped_song_keys_in_aggregate":False,
                    }
                    return (result if failure is None else {}),aggregate


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bliss-db",type=Path,required=True)
    p.add_argument("--feature-db",type=Path,required=True)
    p.add_argument("--repeat-identity-db",type=Path,required=True)
    p.add_argument("--lyrion-library-db",type=Path,required=True)
    p.add_argument("--preflight",action="store_true",
                   help="Only print anonymized readiness counts and blockers, never write files")
    p.add_argument("--out-groups-private",type=Path,
                   help="NEW private JSON required without --preflight")
    p.add_argument("--limit",type=int,default=100)
    p.add_argument("--seed",type=int,default=20261029)
    a=p.parse_args()
    try:
        if not a.preflight:
            if a.out_groups_private is None:
                raise ValueError("New private group output path required")
            if a.out_groups_private.exists() or a.out_groups_private.is_symlink():
                raise FileExistsError("Private group metadata already exists")
        groups,aggregate=generate_private_groups(
            a.bliss_db,a.feature_db,a.repeat_identity_db,a.lyrion_library_db,
            seed=a.seed,limit=a.limit,preflight=a.preflight,
        )
        if not a.preflight:
            if not aggregate["ready_for_grouped_study"]:
                raise ValueError("Refuse incomplete group metadata")
            payload=json.dumps(groups,ensure_ascii=False,indent=2)+"\n"
            with a.out_groups_private.open("x",encoding="utf-8") as handle:
                handle.write(payload)
        # stdout is ALWAYS only non-identifying aggregate counts.
        print(json.dumps(aggregate,indent=2))
    except (ValueError,TypeError,KeyError,OSError,sqlite3.Error):
        p.exit(2,"Read-only Lyrion group derivation failed: identity sources "
                 "or grouped sample are incompatible; no grouped result certified\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
