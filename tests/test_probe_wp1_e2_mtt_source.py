"""Offline WP1-E2 network safety and cache-availability diagnostics tests."""
from __future__ import annotations

from email.message import Message
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import probe_wp1_e2_mtt_source as m


class FakeResponse:
    status = 206
    def __init__(self, url, *, status=206, size=1_000_000_000,
                 payload=None, content_range=None, content_length=None):
        self.url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Range"] = (content_range or
                          f"bytes 0-{m.PROBE_BYTES - 1}/{size}")
        self.headers["Content-Length"] = (content_length or str(m.PROBE_BYTES))
        self.payload = payload if payload is not None else b"x" * m.PROBE_BYTES

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.payload[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SourceProbeTests(unittest.TestCase):
    def test_exact_range_request_never_pulls_zip_or_mp3(self):
        calls = []
        def opener(req, timeout):
            calls.append((req.full_url, req.get_header("Range"),
                          req.get_header("Accept-encoding"), timeout))
            return FakeResponse(req.full_url)
        report = [m.probe_part(p, opener=opener) for p in m.PARTS]
        self.assertEqual([r["status"] for r in report], ["RANGE_206_PASS"]*3)
        self.assertEqual([x[1] for x in calls], ["bytes=0-4095"]*3)
        self.assertEqual([x[3] for x in calls], [20]*3)
        self.assertEqual(m.assess("false", report)["max_requested_response_bytes"],
                         12288)

    def test_status_200_refused_before_reading_unbounded_body(self):
        data = FakeResponse(m.SOURCE+"mp3.zip.001", status=200)
        self.assertEqual(m.probe_part(1, opener=lambda *a, **k: data)["reason"],
                         "HTTP_NOT_206")

    def test_reject_length_range_encoding_and_redirect(self):
        url = m.SOURCE + "mp3.zip.001"
        for response, expected in (
            (FakeResponse(url, content_range="bytes 1-4096/1000000000"),
             "CONTENT_RANGE_MISMATCH"),
            (FakeResponse(url, content_length="999999999"),
             "CONTENT_LENGTH_MISMATCH"),
            (FakeResponse(url, payload=b"x"*100), "TRUNCATED_BOUNDED_RESPONSE"),
            (FakeResponse(url+"-mirror"), "UNEXPECTED_REDIRECT"),
            (FakeResponse(url, size=3_000_000_000), "PART_SIZE_OUT_OF_BOUNDS"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(
                    m.probe_part(1, opener=lambda *a, **k: response)["reason"],
                    expected)

    def test_cache_hit_does_not_claim_vector_availability_or_quality(self):
        probes = [{"part": p, "status": "RANGE_206_PASS"} for p in m.PARTS]
        out = m.assess("true", probes)
        self.assertEqual(out["status"],
                         "CACHE_LOOKUP_HIT_VERIFICATION_STILL_REQUIRED")
        self.assertFalse(out["entire_1019_clip_download_tested"])
        self.assertFalse(out["global_pairwise_fusion_quality_measured"])
        out = m.assess("", probes)
        self.assertEqual(out["status"],
                         "CACHE_MISS_BOUNDED_HTTP_206_PROBES_PASS_ONLY")
        probes[1]["status"] = "BLOCKED"
        self.assertEqual(m.assess("false", probes)["status"],
                         "CACHE_MISS_SOURCE_RANGE_UNAVAILABLE_OR_UNVERIFIED")

    def test_malformed_cache_and_identity_fail_closed(self):
        with self.assertRaises(ValueError):
            m.assess("maybe", [{"part": p, "status": "RANGE_206_PASS"}
                               for p in m.PARTS])
        with self.assertRaises(ValueError):
            m.assess("false", [{"part": 2, "status": "RANGE_206_PASS"}]*3)
        with self.assertRaises(ValueError):
            m.probe_part(4)


if __name__ == "__main__":
    unittest.main()
