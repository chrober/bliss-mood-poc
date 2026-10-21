"""Offline mock for targeted Lyrion songinfo path lookup; no LAN/music writes."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import unquote
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "queue_similarity_pairs_lyrion.ps1"
PLAYER_ID = "01:02:03:04:05:06"
TRACKS = [
    {"id": 11, "url": "file:///mnt/music/Various%2520Artists/Album%252C%25202023/01%2520Song.mp3",
     "decoded": "file:///mnt/music/Various Artists/Album, 2023/01 Song.mp3"},
    {"id": 12, "url": "file:///mnt/music/Band/LP/02-second.flac",
     "decoded": "file:///mnt/music/Band/LP/02-second.flac"},
]


class MockLyrionServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.calls = []
        self.appends = []
        self.rescan = False
        self.corrupt_url = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(size).decode("utf-8"))
        self.server.calls.append(body)
        assert body["method"] == "slim.request"
        assert isinstance(body["params"], list) and len(body["params"]) == 2
        player, command = body["params"]
        assert isinstance(command, list)
        action = command[0]
        if action == "players":
            data = {"players_loop": [
                {"playerid": PLAYER_ID, "connected": "1", "name": "KÃ¼che"},
            ]}
        elif action == "songinfo":
            assert player == "0" and command[-1] == "tags:u"
            assert command[3].startswith("url:file:///")
            candidate = command[3][4:]
            for _ in range(4):
                decoded = unquote(candidate)
                if candidate == decoded:
                    break
                candidate = decoded
            song = next((track for track in TRACKS
                         if track["decoded"] == candidate), None)
            if song:
                url = ("file:///wrong-music-root/01 Song.mp3"
                       if self.server.corrupt_url else song["url"])
                data = {"count": 2, "songinfo_loop": [
                    {"id": song["id"]},
                    {"url": url},
                ]}
            else:
                data = {"count": 0, "songinfo_loop": []}
            if self.server.rescan:
                data["rescan"] = "1"
        elif action == "playlist":
            data = {"_shuffle": 0} if command[1] == "shuffle" else {"_tracks": 3}
        elif action == "playlistcontrol":
            assert player == PLAYER_ID and command[1] == "cmd:add"
            ids = command[2].split(":", 1)[1].split(",")
            self.server.appends.append(ids)
            data = {"count": len(ids)}
        else:
            data = {"error": "unsupported mock command"}
        payload = json.dumps({"id": body["id"], "method": "slim.request",
                              "result": data}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 is required for mock execution")
class QueueScriptIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv = Path(self.tmp.name) / "pairs.csv"
        with self.csv.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(("left", "right", "genre_label", "mood_label"))
            writer.writerow(("Various Artists/Album, 2023/01 Song.mp3",
                             "Band/LP/02-second.flac", "", ""))
        self.server = MockLyrionServer(("127.0.0.1", 0))
        thread = Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def run_script(self, apply=False, root="/mnt/music"):
        env = os.environ.copy()
        env.update({
            "LYRION_SERVER_URL": f"http://127.0.0.1:{self.server.server_port}/jsonrpc.js",
            "LYRION_PLAYER_ID": PLAYER_ID,
            "LYRION_LISTENING_CSV": str(self.csv),
            "LYRION_MUSIC_ROOT": root,
            "LYRION_APPLY": "true" if apply else "false",
        })
        return subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)],
            cwd=SCRIPT.parent.parent, env=env, capture_output=True,
            encoding="utf-8", errors="replace", timeout=40
        )

    def test_dry_run_uses_targeted_full_file_urls_not_entire_77k_catalog(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.appends, [])
        self.assertIn("ID 11", result.stdout)
        self.assertIn("ID 12", result.stdout)
        calls = [c["params"][1][0] for c in self.server.calls]
        self.assertTrue("songinfo" in calls)
        self.assertFalse("titles" in calls)
        self.assertLessEqual(calls.count("songinfo"), 6)

    def test_explicit_apply_appends_two_ids_in_csv_order(self):
        result = self.run_script(apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.appends, [["11", "12"]])

    def test_different_music_root_must_fail_with_no_queue_change(self):
        result = self.run_script(apply=True, root="/wrong/music")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("erwartet: 1", result.stderr + result.stdout)
        self.assertEqual(self.server.appends, [])

    def test_server_returned_id_but_mismatched_url_must_be_rejected(self):
        self.server.corrupt_url = True
        result = self.run_script(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("erwartet: 1", result.stderr)
        self.assertEqual(self.server.appends, [])

    def test_rescan_must_not_add(self):
        self.server.rescan = True
        result = self.run_script(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.server.appends, [])


if __name__ == "__main__":
    unittest.main()
