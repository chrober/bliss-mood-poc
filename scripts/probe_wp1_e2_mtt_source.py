#!/usr/bin/env python3
"""WP1-E2: bounded, metadata-only MTT HTTP-206 access preflight.

Never downloads MP3 clips, full multipart ZIPs, weights, or song vectors.
A passing probe only proves three small range requests work at this instant;
it DOES NOT prove 1,019 clip ranges will complete. No source URLs are configurable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCHEMA = "wp1-e2-mtt-source-range-diagnostic-v1"
SOURCE = "https://mirg.city.ac.uk/datasets/magnatagatune/"
PARTS = (1, 2, 3)
PROBE_BYTES = 4096
MIN_PART_BYTES = 500_000_000
MAX_PART_BYTES = 1_500_000_000
TIMEOUT_SECONDS = 20
CONTENT_RANGE = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$")


def verify_response(status, headers, resolved_url, expected_url, data):
    """Verify a genuinely bounded response, not an ignored HTTP Range."""
    if status != 206:
        raise ValueError("HTTP_NOT_206")
    if resolved_url != expected_url:
        raise ValueError("UNEXPECTED_REDIRECT")
    if headers.get("Content-Encoding", "identity").lower() != "identity":
        raise ValueError("CONTENT_ENCODING_CHANGED")
    match = CONTENT_RANGE.fullmatch(headers.get("Content-Range", "").strip())
    if match is None:
        raise ValueError("CONTENT_RANGE_MISSING")
    start, end, total = (int(x) for x in match.groups())
    if (start, end) != (0, PROBE_BYTES-1):
        raise ValueError("CONTENT_RANGE_MISMATCH")
    if not MIN_PART_BYTES < total < MAX_PART_BYTES:
        raise ValueError("PART_SIZE_OUT_OF_BOUNDS")
    length_header = headers.get("Content-Length")
    if length_header is not None and length_header != str(PROBE_BYTES):
        raise ValueError("CONTENT_LENGTH_MISMATCH")
    if len(data) != PROBE_BYTES:
        raise ValueError("TRUNCATED_BOUNDED_RESPONSE")
    return total


def probe_part(part, opener=urlopen):
    if part not in PARTS:
        raise ValueError("INVALID_PART")
    url = SOURCE + f"mp3.zip.{part:03d}"
    request = Request(url, headers={
        "Range": f"bytes=0-{PROBE_BYTES-1}",
        "Accept-Encoding": "identity",
        "User-Agent": "bliss-mood-poc-wp1-source-availability/1.0",
    })
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            headers = response.headers
            resolved_url = response.geturl()
            if status != 206:
                raise ValueError("HTTP_NOT_206")
            # Validate Content-Range before reading any body.
            verify_response(status, headers, resolved_url, url,
                            b"\0" * PROBE_BYTES)
            # At most 4097 bytes are ever consumed (never whole source ZIP).
            body = response.read(PROBE_BYTES + 1)
            size = verify_response(status, headers, resolved_url, url, body)
            return {"part": part, "status": "RANGE_206_PASS", "part_bytes": size}
    except HTTPError as error:
        return {"part": part, "status": "HTTP_BLOCKED", "http_code": error.code}
    except (ValueError, URLError, TimeoutError, OSError) as error:
        if isinstance(error, ValueError):
            reason = str(error)
        elif isinstance(error, TimeoutError):
            reason = "TIMEOUT"
        else:
            reason = "TRANSPORT_FAILURE"
        return {"part": part, "status": "BLOCKED", "reason": reason}


def assess(cache_lookup: str, probes: list[dict]):
    if cache_lookup not in ("true", "false", ""):
        raise ValueError("Expected exact cache lookup state")
    if len(probes) != 3 or [p["part"] for p in probes] != list(PARTS):
        raise ValueError("Every official multipart ZIP part must be probed")
    passed = all(p["status"] == "RANGE_206_PASS" for p in probes)
    cache = "SCOPED_CACHE_LOOKUP_HIT" if cache_lookup == "true" else "SCOPED_CACHE_MISS"
    if cache_lookup == "true":
        state = "CACHE_LOOKUP_HIT_VERIFICATION_STILL_REQUIRED"
    elif passed:
        state = "CACHE_MISS_BOUNDED_HTTP_206_PROBES_PASS_ONLY"
    else:
        state = "CACHE_MISS_SOURCE_RANGE_UNAVAILABLE_OR_UNVERIFIED"
    return {
        "schema": SCHEMA,
        "status": state,
        "cache_scope": "current_branch_and_default_branch_only",
        "scoped_cache_lookup": cache,
        "probes": probes,
        "probes_per_part": 1,
        "max_requested_response_bytes": len(PARTS) * PROBE_BYTES,
        "entire_1019_clip_download_tested": False,
        "full_audio_download_allowed": False,
        "global_pairwise_fusion_quality_measured": False,
        "independent_musical_similarity_validated": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-hit", choices=("", "true", "false"), default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = assess(args.cache_hit, [probe_part(p) for p in PARTS])
    # Never overwrite reports. Only aggregate source status and sizes.
    with open(args.out, "x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
