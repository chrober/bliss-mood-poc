"""WP3: genuine-source-shaped Lyrion group bridge, all data synthetic."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_run_local_bliss_essentia_teacher_study import LocalPairedStudyTests
import derive_lyrion_research_groups as bridge


class ResearchLyrionGroupsTests(unittest.TestCase):
    def setUp(self):
        source=LocalPairedStudyTests("test_real_source_adapters_aggregate_only_no_writes")
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.source=source
        self.root=source.root
        self.snapshot=self.root/"artist-repeat-identities.sqlite"
        self.library=self.root/"library.db"
        with closing(sqlite3.connect(self.snapshot)) as conn:
            conn.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE track_identity(
                    database_file TEXT PRIMARY KEY, lms_track_id INTEGER,
                    lms_urlmd5 TEXT, recording_mbid TEXT);
                CREATE TABLE track_artist_identity(
                    database_file TEXT NOT NULL, role TEXT NOT NULL,
                    canonical_key TEXT NOT NULL);
            """)
            conn.execute("INSERT INTO metadata VALUES(?,?)",
                         ("schema_identity","lyrion-track-identities-v1"))
            for i,key in enumerate(source.all_groups):
                mbid=str(uuid.uuid5(uuid.NAMESPACE_DNS,f"recording-{i}"))
                conn.execute("INSERT INTO track_identity VALUES(?,?,?,?)",
                             (key,i+1,"urlmd5-"+str(i),mbid))
                conn.execute("INSERT INTO track_artist_identity VALUES(?,?,?)",
                             (key,"ARTIST","artist-mbid-"+str(i//8)))
                # Collaborative song: record both credited artists.
                if i==8:
                    conn.execute("INSERT INTO track_artist_identity VALUES(?,?,?)",
                                 (key,"TRACKARTIST","artist-mbid-"+str(0)))
            conn.commit()
        with closing(sqlite3.connect(self.library)) as conn:
            conn.executescript("""
                CREATE TABLE tracks(
                    id INTEGER PRIMARY KEY,urlmd5 TEXT,musicbrainz_id TEXT,
                    album INTEGER,remote INTEGER,audio INTEGER);
                CREATE TABLE albums(id INTEGER PRIMARY KEY);
            """)
            for album in range(8):
                conn.execute("INSERT INTO albums VALUES(?)",(album+100,))
            for i,key in enumerate(source.all_groups):
                mbid=str(uuid.uuid5(uuid.NAMESPACE_DNS,f"recording-{i}"))
                conn.execute("INSERT INTO tracks VALUES(?,?,?,?,?,?)",
                             (i+1,"urlmd5-"+str(i),mbid,i//8+100,0,1))
            conn.commit()
        self.out=self.root/"private-derived-groups.json"

    def derive(self):
        return bridge.generate_private_groups(
            self.source.bliss,self.source.essentia,self.snapshot,
            self.library,seed=20261029,limit=64
        )

    def test_uses_real_snapshot_link_and_lms_album_ids_no_path_guess(self):
        original=[p.read_bytes() for p in (
            self.source.bliss,self.source.essentia,self.snapshot,self.library
        )]
        groups,aggregate=self.derive()
        self.assertEqual(len(groups),64)
        self.assertEqual(aggregate["counts"]["paired_tracks_with_verified_lms_artist_album"],64)
        self.assertGreaterEqual(aggregate["artist_album_recording_connected_components"],2)
        self.assertEqual(aggregate["train_songs"]+aggregate["holdout_songs"],64)
        self.assertTrue(aggregate["snapshot_lms_id_urlmd5_checked"])
        self.assertNotIn("Private Audio",json.dumps(aggregate))
        self.assertNotIn(str(self.root),json.dumps(aggregate))
        items=list(groups.values())
        self.assertTrue(all("album_group" in x and "recording_group" in x for x in items))
        self.assertEqual(original,[p.read_bytes() for p in (
            self.source.bliss,self.source.essentia,self.snapshot,self.library
        )])

    def test_collaborator_artist_connection_not_split(self):
        groups,_=self.derive()
        keys=list(self.source.all_groups)
        # Artist 0 and artist 1 are connected by one collaboration.
        self.assertEqual(groups[keys[0]]["artist_group"],groups[keys[8]]["artist_group"])

    def test_stale_snapshot_md5_is_not_silently_accepted(self):
        with closing(sqlite3.connect(self.library)) as conn:
            conn.execute("UPDATE tracks SET urlmd5=? WHERE id=1",("changed-urlmd5",))
            conn.commit()
        with self.assertRaisesRegex(ValueError,"lack verifiable library"):
            self.derive()

    def test_unknown_recordings_in_same_conservative_group(self):
        with closing(sqlite3.connect(self.library)) as conn:
            conn.execute("UPDATE tracks SET musicbrainz_id=NULL WHERE id IN (1,2)")
            conn.commit()
        with closing(sqlite3.connect(self.snapshot)) as conn:
            conn.execute("UPDATE track_identity SET recording_mbid=NULL WHERE lms_track_id IN (1,2)")
            conn.commit()
        groups,aggregate=self.derive()
        keys=list(self.source.all_groups)
        self.assertEqual(groups[keys[0]]["recording_group"],
                         bridge.UNKNOWN_RECORDING)
        self.assertEqual(groups[keys[1]]["recording_group"],
                         bridge.UNKNOWN_RECORDING)
        self.assertEqual(aggregate["counts"]["recording_mbid_unavailable"],2)

    def test_missing_artist_credit_fails_without_generating_output(self):
        with closing(sqlite3.connect(self.snapshot)) as conn:
            conn.execute("DELETE FROM track_artist_identity WHERE database_file=?",
                         (next(iter(self.source.all_groups)),))
            conn.commit()
        with self.assertRaisesRegex(ValueError,"lack verifiable library"):
            self.derive()
        self.assertFalse(self.out.exists())

    def test_private_file_creation_is_new_only(self):
        with patch.object(sys,"argv",[
            "derive","--bliss-db",str(self.source.bliss),
            "--feature-db",str(self.source.essentia),
            "--repeat-identity-db",str(self.snapshot),
            "--lyrion-library-db",str(self.library),
            "--out-groups-private",str(self.out),"--limit","64"
        ]):
            self.assertEqual(bridge.main(),0)
        payload=json.loads(self.out.read_text())
        self.assertEqual(len(payload),64)
        old=self.out.read_bytes()
        with patch.object(sys,"argv",[
            "derive","--bliss-db",str(self.source.bliss),
            "--feature-db",str(self.source.essentia),
            "--repeat-identity-db",str(self.snapshot),
            "--lyrion-library-db",str(self.library),
            "--out-groups-private",str(self.out),"--limit","64"
        ]):
            with self.assertRaises(SystemExit):
                bridge.main()
        self.assertEqual(self.out.read_bytes(),old)


if __name__=="__main__":
    unittest.main()
