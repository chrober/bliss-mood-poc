"""Synthetic-only gates: NEW research cohort excludes all prior artist/album/recording identities."""
from __future__ import annotations
from contextlib import closing, redirect_stdout
import io
import json
import math
from pathlib import Path
import sqlite3
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from test_derive_lyrion_research_groups import ResearchLyrionGroupsTests
from test_run_local_bliss_essentia_teacher_study import _sha
from audit_bliss_essentia_join import BLISS_COLUMNS
from build_wp3_research_db import build
import prepare_wp3_independent_cohort as planning


class IndependentCohortTests(unittest.TestCase):
    def setUp(self):
        x=ResearchLyrionGroupsTests(
            "test_uses_real_snapshot_link_and_lms_album_ids_no_path_guess")
        x.setUp()
        self.addCleanup(x.doCleanups)
        self.x=x
        self.old=x.root/"old-grouped-research.sqlite"
        self.out=x.root/"private-independent-cohort.json"
        report=build(x.source.bliss,x.source.essentia,self.old,
                     snapshot=x.snapshot,library=x.library,limit=64)
        self.assertEqual(report["groups"]["status"],"READY")
        # A bounded synthetic future library; all titles and file paths are
        # fictional; no real listener/source data in CI.
        base=sorted(x.source.all_groups)[0]
        self.first_prior=base
        self.candidate_names={}
        with closing(sqlite3.connect(x.source.bliss)) as bliss, \
             closing(sqlite3.connect(x.snapshot)) as sn, \
             closing(sqlite3.connect(x.library)) as lib:
            for j in range(110):
                key=f"Private Future Artist {j}/Track {j}.flac"
                mbid=str(uuid.uuid5(uuid.NAMESPACE_DNS,f"future-recording-{j}"))
                tid=1000+j
                album=9000+j
                artist=f"future-canonical-artist-{j}"
                if j==1:
                    # A new track with reused PRIOR artist credit: exclude it.
                    artist="artist-mbid-0"
                if j==2:
                    # A new different artist on a PRIOR album: exclude.
                    album=100
                if j==3:
                    # Unknown recording identity: exclude.
                    mbid=None
                if j==4:
                    # Existing prior recording UUID: exclude.
                    with closing(sqlite3.connect(x.snapshot)) as tmp:
                        mbid=tmp.execute(
                            "SELECT recording_mbid FROM track_identity WHERE lms_track_id=1"
                        ).fetchone()[0]
                if j==5:
                    # Reuse an exact prior track key: cannot be new.
                    key=base
                if j==6:
                    # Artist collaboration has one prior artist: exclude.
                    pass
                rows=[float(0.05+((j+k*9)%27)/30.0) for k in range(23)]
                rows[0]=float(j+40)
                rows[2]=float(j%17)
                bliss.execute(
                    f'INSERT INTO TracksV2 VALUES ({",".join("?" for _ in range(24))})',
                    (key,*rows))
                if album != 100:
                    lib.execute("INSERT INTO albums VALUES (?)",(album,))
                lib.execute("INSERT INTO tracks VALUES (?,?,?,?,?,?)",
                            (tid,"md5-future-"+str(j),mbid,album,0,1))
                if j != 5:
                    sn.execute("INSERT INTO track_identity VALUES (?,?,?,?)",
                               (key,tid,"md5-future-"+str(j),mbid))
                    sn.execute("INSERT INTO track_artist_identity VALUES (?,?,?)",
                               (key,"ARTIST",artist))
                    if j==6:
                        sn.execute("INSERT INTO track_artist_identity VALUES (?,?,?)",
                                   (key,"TRACKARTIST","artist-mbid-1"))
                self.candidate_names[j]=key
            bliss.commit()
            sn.commit()
            lib.commit()

    def _plan(self,count=24):
        return planning.plan(self.x.source.bliss,self.x.snapshot,
                             self.x.library,self.old,count=count)

    def test_new_cohort_is_source_and_artist_disjoint(self):
        paths=(self.x.source.bliss,self.x.snapshot,self.x.library,self.old)
        hashes=tuple(_sha(p) for p in paths)
        man,report=self._plan(50)
        self.assertEqual(len(man["selected_songs"]),50)
        self.assertEqual(report["new_songs"],50)
        self.assertEqual(report["prior_research_songs_excluded"],64)
        self.assertTrue(report["mutually_nonoverlapping_artist_album_recording_identities"])
        self.assertTrue(report["essentia_on_new_songs_available"] is False)
        selected={r["track_file"] for r in man["selected_songs"]}
        for i in range(7):
            self.assertNotIn(self.candidate_names[i],selected)
        artist=set()
        album=set()
        mbid=set()
        for r in man["selected_songs"]:
            self.assertTrue(artist.isdisjoint(r["artist_keys"]))
            artist.update(r["artist_keys"])
            self.assertNotIn(r["lms_album_id"],album)
            album.add(r["lms_album_id"])
            self.assertNotIn(r["recording_mbid"],mbid)
            mbid.add(r["recording_mbid"])
        self.assertEqual(hashes,tuple(_sha(p) for p in paths))
        self.assertFalse(self.out.exists())
        self.assertFalse((self.x.root/"old-grouped-research.sqlite-wal").exists())
        self.assertNotIn("Private Future Artist",json.dumps(report))
        self.assertNotIn(str(self.x.root),json.dumps(report))

    def test_deterministic_even_if_called_twice(self):
        a,r1=self._plan(30)
        b,r2=self._plan(30)
        self.assertEqual(a,b)
        self.assertEqual(r1,r2)

    def test_old_grouped_snapshot_not_ready_fails_closed(self):
        with closing(sqlite3.connect(self.old)) as db:
            db.execute("UPDATE metadata SET value='NOT_AVAILABLE' WHERE key='group_readiness'")
            db.commit()
        with self.assertRaisesRegex(ValueError,"source-verified and grouped"):
            self._plan()

    def test_old_lms_id_drift_fails_closed(self):
        with closing(sqlite3.connect(self.x.library)) as db:
            db.execute("UPDATE tracks SET urlmd5='drifted' WHERE id=1")
            db.commit()
        with self.assertRaisesRegex(ValueError,"Old cohort identity changed"):
            self._plan()

    def test_no_guess_when_not_enough_independent_songs(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):
            self._plan(200)

    def test_cli_preflight_does_not_write_and_manifest_exclusive(self):
        args=["candidate","--bliss-db",str(self.x.source.bliss),
              "--repeat-identity-db",str(self.x.snapshot),
              "--lyrion-library-db",str(self.x.library),
              "--prior-research-db",str(self.old),
              "--seed","20261030","--count","25"]
        stdout=io.StringIO()
        with patch.object(sys,"argv",args+["--preflight"]),redirect_stdout(stdout):
            self.assertEqual(planning.main(),0)
        self.assertFalse(self.out.exists())
        self.assertEqual(json.loads(stdout.getvalue())["new_songs"],25)
        self.assertNotIn("Private Future Artist",stdout.getvalue())
        stdout=io.StringIO()
        with patch.object(sys,"argv",args+["--out-private",str(self.out)]),redirect_stdout(stdout):
            self.assertEqual(planning.main(),0)
        self.assertTrue(self.out.exists())
        old_bytes=self.out.read_bytes()
        with patch.object(sys,"argv",args+["--out-private",str(self.out)]):
            with self.assertRaises(SystemExit) as exc:
                planning.main()
        self.assertEqual(exc.exception.code,2)
        self.assertEqual(old_bytes,self.out.read_bytes())


if __name__=="__main__":
    unittest.main()
