#!/usr/bin/env python3
"""Validate PRIVATE read-only copied Lyrion metadata SQLite files.

No raw tracks, artist names, paths, hashes or data rows printed.
Use as a Python 3.15 script FILE, never inline python -c through PowerShell 5.1.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys

SCHEMA = "lyrion-track-identities-v1"
REQUIRED_SNAPSHOT = {
    "metadata": {"key", "value"},
    "track_identity": {"database_file", "lms_track_id", "lms_urlmd5", "recording_mbid"},
    "track_artist_identity": {"database_file", "role", "canonical_key"},
}
REQUIRED_LIBRARY = {
    "tracks": {"id", "urlmd5", "musicbrainz_id", "album", "remote", "audio"},
    "albums": {"id"},
}


def _read_only_db(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("A local source SQLite is missing")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def _validate(con: sqlite3.Connection, required: dict[str, set[str]]) -> None:
    if con.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise ValueError("Copied SQLite quick_check failed")
    for name, expected in required.items():
        fields = {r[1] for r in con.execute(f"PRAGMA table_info({name})")}
        if not expected <= fields:
            raise ValueError("Copied SQLite has incompatible schema")


def inspect(library: Path, snapshot: Path) -> dict:
    if library.resolve() == snapshot.resolve():
        raise ValueError("Library and identity snapshot must be distinct")
    with closing(_read_only_db(library)) as lms:
        with closing(_read_only_db(snapshot)) as lab:
            _validate(lms, REQUIRED_LIBRARY)
            _validate(lab, REQUIRED_SNAPSHOT)
            meta = dict(lab.execute("SELECT key, value FROM metadata"))
            if meta.get("schema_identity") != SCHEMA:
                raise ValueError("Unexpected BlissMixerLab snapshot schema")
            scan = meta.get("lms_scan_time", "")
            fingerprint = meta.get("media_roots_identity", "")
            if not isinstance(scan, str) or not scan.isdigit() or int(scan) <= 0:
                raise ValueError("Missing valid scan time")
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", fingerprint):
                raise ValueError("Missing valid music-root fingerprint")
            result = {
                "schema": "wp3-lyrion-local-copies-validation-v1",
                "status": "COPIED_SQLITES_VALID_INDIVIDUALLY_CROSS_SOURCE_PREFLIGHT_PENDING",
                "library_tracks": lms.execute("SELECT COUNT(*) FROM tracks").fetchone()[0],
                "library_albums": lms.execute("SELECT COUNT(*) FROM albums").fetchone()[0],
                "snapshot_tracks": lab.execute("SELECT COUNT(*) FROM track_identity").fetchone()[0],
                "snapshot_artist_identity_rows": lab.execute("SELECT COUNT(*) FROM track_artist_identity").fetchone()[0],
                "snapshot_scan_time": int(scan),
                "snapshot_roots_hash_well_formed": True,
                "each_source_read_only_quick_check_ok": True,
                "snapshot_library_mutual_consistency_not_yet_certified": True,
            }
            return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lyrion-library-db", type=Path, required=True)
    p.add_argument("--repeat-identity-db", type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(inspect(a.lyrion_library_db, a.repeat_identity_db),
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, sqlite3.Error, TypeError, OverflowError):
        p.exit(2, "WP3 copied metadata SQLite validation blocked: source missing, malformed, or inconsistent schema\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
