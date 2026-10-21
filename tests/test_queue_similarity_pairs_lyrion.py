"""Private-LAN-free end-to-end mock of Lyrion JSON-RPC playlist pair queue."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "queue_similarity_pairs_lyrion.ps1"
PLAYER_ID = "01:02:03:04:05:06"
TRACKS = [
    {"id": 11, "url": "file:///mnt/music/Various%2520Artists/Album%252C%25202023/01%2520Song.mp3"},
    {"id": 12, "url": "file:///mnt/music/Band/LP/02-second.flac"},
    {"id": 13, "url": "file:///other/A/01%20Song.mp3"},  # same filename, wrong full path
    {"id": 14, "url": "file:///somewhere/irrelevant.wav"},
]


class MockLyrionServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.tracks = list(TRACKS)
        self.calls = []
        self.appends = []
        self.rescan = False


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
        elif action == "titles":
            assert player == "0"
            assert command[-1] == "tags:u"
            start, page_size = int(command[1]), int(command[2])
            rows = self.server.tracks[start:start + page_size]
            data = {"count": len(self.server.tracks), "titles_loop": rows}
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

    def run_script(self, apply=False):
        env = os.environ.copy()
        env.update({
            "LYRION_SERVER_URL": f"http://127.0.0.1:{self.server.server_port}/jsonrpc.js",
            "LYRION_PLAYER_ID": PLAYER_ID,
            "LYRION_LISTENING_CSV": str(self.csv),
            "LYRION_APPLY": "true" if apply else "false",
        })
        return subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)],
            cwd=SCRIPT.parent.parent, env=env, capture_output=True,
            encoding="utf-8", errors="replace", timeout=40
        )

    def test_dry_run_reads_all_ids_never_modifies_existing_queue(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.appends, [])
        self.assertIn("ID 11", result.stdout)
        self.assertIn("ID 12", result.stdout)
        self.assertTrue(any(
            call["params"][1][0] == "titles" for call in self.server.calls
        ))
        self.assertFalse(any(
            call["params"][1][0] == "songinfo" for call in self.server.calls
        ))

    def test_explicit_apply_appends_two_ids_in_csv_order(self):
        result = self.run_script(apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.appends, [["11", "12"]])

    def test_matching_across_multiple_lms_catalog_pages(self):
        self.server.tracks = [
            {"id": 1000 + i, "url": f"file:///music/Noise/Subfolder/noise-{i}.mp3"}
            for i in range(515)
        ] + list(TRACKS)
        result = self.run_script(apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.appends, [["11", "12"]])
        pages = [call["params"][1] for call in self.server.calls
                 if call["params"][1][0] == "titles"]
        self.assertEqual([int(page[1]) for page in pages], [0, 500])

    def test_duplicate_full_relative_path_in_two_music_roots_is_ambiguous(self):
        self.server.tracks.append({
            "id": 99,
            "url": "file:///duplicate/root/Various%20Artists/Album%2C%202023/01%20Song.mp3",
        })
        result = self.run_script(apply=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("erwartet: 1", result.stderr)
        self.assertEqual(self.server.appends, [])

    def test_catalog_change_or_no_match_never_adds(self):
        self.server.rescan = True
        result = self.run_script(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.server.appends, [])


if __name__ == "__main__":
    unittest.main()
