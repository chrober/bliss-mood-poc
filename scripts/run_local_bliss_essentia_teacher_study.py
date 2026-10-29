#!/usr/bin/env python3
"""WP3-R3: permissioned LOCAL joint Bliss/Essentia research, aggregate-only.

Inputs are existing READ-ONLY Bliss SQLite, Essentia schema-v3 sidecar, and
PRIVATE exact-key artist/album/recording metadata. No raw song features,
labels, keys, hashes, model matrices, or private paths in published results.
No access to private files until an operator explicitly supplies all sources.
No audio scan, ONNX, Lyrion calls, or network. Fails closed on missing groups.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
import math
import struct
from pathlib import Path
import sqlite3
import sys

from audit_bliss_essentia_join import (
    open_bliss, bliss_vector, compatible_essentia_provenance,
)
import evaluate_similarity as ev
from research_feature_relationships import relationship_report
from research_bliss_essentia_teacher_models import model_report
from research_bliss_only_teacher_geometry import proxy_geometry_report

MIN_JOINT = 24
MAX_JOINT = 4000
MAX_GROUP_BYTES = 8 * 1024 * 1024


def _file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def _read_private_groups(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_GROUP_BYTES:
        raise ValueError("Private groups file absent or excessive size")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data or len(data) > 200_000:
        raise ValueError("Invalid exact-key private group JSON")
    # Group data is private: do not return it in the report.
    for key, meta in data.items():
        if (not isinstance(key, str) or not key or "\x00" in key
                or not isinstance(meta, dict)
                or any(not isinstance(meta.get(field),str)
                       or not meta[field].strip() or "\x00" in meta[field]
                       for field in ("artist_group","album_group","recording_group"))):
            raise ValueError("Invalid private artist/album/recording group metadata")
    return data


def _pair_rows(
    bliss_db: Path, feature_db: Path, groups: dict, *,
    seed: int, limit: int,
) -> tuple[list[dict], dict]:
    if type(limit) is not int or not MIN_JOINT <= limit <= MAX_JOINT:
        raise ValueError("Study limit outside supported 24..4000 interval")
    if type(seed) is not int:
        raise ValueError("Invalid deterministic study seed")
    counters={
        "head_pair_sample":0,
        "eligible_head_pair_population":0,
        "invalid_head_vectors_in_population":0,
        "head_provenance_rejected":0,
        "bliss_missing_or_ambiguous_or_invalid":0,
        "group_metadata_missing":0,
        "paired_grouped_songs_accepted":0,
    }
    rows=[]
    # Files exist is checked in the open helpers. Both have PRAGMA query_only.
    with closing(open_bliss(bliss_db)) as bliss:
        with closing(ev.open_database(feature_db)) as essentia:
            cohorts={name:ev._catalog(essentia,name,experimental=True)
                     for name in ("genre","moodtheme")}
            if len({c["preprocessing_version"] for c in cohorts.values()}) != 1:
                raise ValueError("Classifier preprocessings are incompatible")
            sample=ev.load_sample(essentia,cohorts,limit,seed)
            counters["head_pair_sample"]=sample["sample_size"]
            counters["eligible_head_pair_population"]=sample["valid_total"]
            counters["invalid_head_vectors_in_population"]=sample["invalid"]
            for key,vectors in sample["tracks"].items():
                if compatible_essentia_provenance(essentia,key,cohorts) is None:
                    counters["head_provenance_rejected"]+=1
                    continue
                status,bliss_values=bliss_vector(bliss,key)
                if status != "valid":
                    counters["bliss_missing_or_ambiguous_or_invalid"]+=1
                    continue
                if key not in groups:
                    counters["group_metadata_missing"]+=1
                    continue
                row={"track_id":key,"bliss":bliss_values,
                     "genre":vectors["genre"],"moodtheme":vectors["moodtheme"]}
                row.update({field:groups[key][field]
                            for field in ("artist_group","album_group","recording_group")})
                rows.append(row)
            counters["paired_grouped_songs_accepted"]=len(rows)
            if len(rows) < MIN_JOINT:
                raise ValueError("Too few exact-key paired songs with private group provenance")
            if counters["group_metadata_missing"]:
                # Do not silently alter the target by discarding songs with no groups.
                raise ValueError("The paired cohort has incomplete group provenance")
            return rows, {
                "schema":"bliss_essentia_real_join_aggregate_v1",
                "sample_seed":seed,
                "requested_max_head_pair_sample":limit,
                "selected_genre_head_experimentally_validated":cohorts["genre"]["validated"],
                "selected_mood_head_experimentally_validated":cohorts["moodtheme"]["validated"],
                "counts":counters,
                "cross_db_audio_byte_identity_certified":False,
                "essentia_teacher_pretrained_data_overlap_ruled_out":False,
                "artist_album_recording_groups_explicitly_required":True,
                "private_song_or_model_hashes_returned":False,
            }


def _study_rows(rows: list[dict], coverage: dict, *, seed: int) -> dict:
    # All fitted transformations use the same group-disjoint train/holdout.
    corrs=relationship_report(rows,seed=seed)
    teacher=model_report(rows,seed=seed)
    geometry=proxy_geometry_report(rows,seed=seed)
    return {
        "schema":"local_bliss_essentia_teacher_only_development_aggregate_v1",
        "status":"EXPLORATORY_DEVELOPMENT_NOT_GENERAL_SIMILARITY_VALIDATION",
        "coverage":coverage,
        "correlations":corrs,
        "teacher_predictions":teacher,
        "bliss_only_geometry_proxy":geometry,
        "validation": {
            "split":"same_group_connected_25pct_holdout_seeded",
            "association_significance_established":False,
            "bliss_musical_similarity_improvement_established":False,
            "user_specific_learning_performed":False,
            "source_music_scanned_or_written":False,
            "individual_song_feature_artifacts_saved":False,
        }
    }



def run_study(
    bliss_db: Path, feature_db: Path, private_groups_json: Path, *,
    seed: int = 20261029, limit: int = 400,
) -> dict:
    groups=_read_private_groups(private_groups_json)
    rows,coverage=_pair_rows(bliss_db,feature_db,groups,seed=seed,limit=limit)
    return _study_rows(rows,coverage,seed=seed)


def run_research_database(research_db: Path, *, seed: int = 20261029) -> dict:
    """Read only the new, self-contained PRIVATE research snapshot.

    Never invent group IDs; missing/blocked group provenance denies all
    supervised correlations, teacher reconstruction and geometry learning.
    """
    if not research_db.is_file():
        raise ValueError("Research database not found")
    rows = []
    with closing(sqlite3.connect(research_db.resolve().as_uri() + "?mode=ro",
                                 uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version != 1:
            raise ValueError("Unknown WP3 research snapshot version")
        props = dict(conn.execute("SELECT key,value FROM metadata"))
        if (props.get("schema") != "lyrion-wp3-research-snapshot-v1"
                or props.get("group_readiness") != "READY"):
            raise ValueError("Group-disjoint research blocked until verified Lyrion metadata is available")
        cohort = json.loads(props["selection_json"])
        if int(cohort["sample_seed"]) != seed:
            raise ValueError("Research cohort seed differs from trained split seed")
        cursor = conn.execute("""
            SELECT track_key, bliss_f64_le, genre_f32_le, moodtheme_f32_le,
                   artist_group, album_group, recording_group
              FROM paired_tracks ORDER BY track_key COLLATE BINARY
        """)
        for key, bliss_blob, genre_blob, mood_blob, artist, album, recording in cursor:
            if (not isinstance(key,str) or not key or "\0" in key
                    or not isinstance(bliss_blob,bytes) or len(bliss_blob)!=23*8
                    or any(not isinstance(group,str) or not group.strip()
                           for group in (artist,album,recording))):
                raise ValueError("Malformed research feature or group identity")
            bliss = struct.unpack("<23d",bliss_blob)
            genre = ev.decode_blob(genre_blob,87)
            mood = ev.decode_blob(mood_blob,56)
            if (not all(math.isfinite(x) for x in bliss)
                    or genre is None or mood is None):
                raise ValueError("Malformed private research vectors")
            rows.append({
                "track_id": key, "bliss": bliss,
                "genre": genre, "moodtheme": mood,
                "artist_group": artist, "album_group": album,
                "recording_group": recording,
            })
    if not MIN_JOINT <= len(rows) <= MAX_JOINT:
        raise ValueError("Research cohort outside supported bounds")
    coverage = {
        "schema": "bliss_essentia_single_sqlite_grouped_snapshot_aggregate_v1",
        "sample_seed": seed,
        "selected_genre_head_experimentally_validated": bool(
            cohort["chosen_head_model_ids"]["genre"]["validated_against_essentia"]),
        "selected_mood_head_experimentally_validated": bool(
            cohort["chosen_head_model_ids"]["moodtheme"]["validated_against_essentia"]),
        "counts": {"paired_grouped_songs_accepted":len(rows)},
        "cross_db_audio_byte_identity_certified":False,
        "essentia_teacher_pretrained_data_overlap_ruled_out":False,
        "artist_album_recording_groups_explicitly_required":True,
        "private_song_or_model_hashes_returned":False,
    }
    return _study_rows(rows,coverage,seed=seed)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--research-db",type=Path,
                   help="New private single SQLite WP3 snapshot; no original DB paths required")
    p.add_argument("--bliss-db",type=Path)
    p.add_argument("--feature-db",type=Path)
    p.add_argument("--group-metadata-json",type=Path)
    p.add_argument("--limit",type=int,default=400)
    p.add_argument("--seed",type=int,default=20261029)
    p.add_argument("--out",required=True,type=Path,
                   help="New private aggregate JSON; NEVER overwrites existing files")
    args=p.parse_args()
    try:
        if args.out.exists():
            raise FileExistsError("Aggregate output exists")
        # Do not attempt to normalize/trust a music path inferred from user info.
        if args.research_db is not None:
            if any(x is not None for x in (
                    args.bliss_db,args.feature_db,args.group_metadata_json)):
                raise ValueError("Use either research DB or original three inputs")
            result=run_research_database(args.research_db,seed=args.seed)
        else:
            if any(x is None for x in (
                    args.bliss_db,args.feature_db,args.group_metadata_json)):
                raise ValueError("Original research inputs are incomplete")
            result=run_study(args.bliss_db,args.feature_db,args.group_metadata_json,
                             seed=args.seed,limit=args.limit)
        # Never echo private source filenames, hashes or keys on an exception.
        payload=json.dumps(result,allow_nan=False,indent=2)+"\n"
        with args.out.open("x",encoding="utf-8") as handle:
            handle.write(payload)
        print(json.dumps({"schema":result["schema"],
                          "status":result["status"],
                          "paired_grouped_songs":result["coverage"]["counts"][
                              "paired_grouped_songs_accepted"],
                          "local_private_aggregate_created":True},indent=2))
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error,RuntimeError,
            OverflowError):
        p.exit(2,"Local research failed safely: check exact input schemas, group "
                 "coverage, read-only databases and installed statistical packages\n")
    return 0


if __name__=="__main__":
    sys.exit(main())
