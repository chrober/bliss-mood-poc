#!/usr/bin/env python3
"""Private, fail-closed same-100-track Rust-v5 -> native Essentia similarity bridge.

prepare: validate the original read-only feature cohort, embedding exports,
source-audio hashes, ONNX/class metadata and scanner/worker SHA256; then write
a *new* manifest, provenance record and empty native export directory.
compare: check native outputs against the frozen manifest and original data,
verify distinct frontend identities and identical model weights/labels, and
measure numeric + 4,950-pair rank drift without exposing song keys.
No original DB, music, embedding or hearing-rating files are ever modified.
"""
from __future__ import annotations

import argparse
import csv
import io
from contextlib import closing
import hashlib
import itertools
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import statistics
import struct
import sys

N = 100
OLD_FRONTEND = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated"
NATIVE_PREFIX = "experimental-essentia-cpp-dsp"
DIMENSIONS = {"genre": 87, "moodtheme": 56, "voice": 2}
EXPECTED_MODELS = {
    "genre": ("mtg_jamendo_genre-discogs-effnet-1.onnx",
              "mtg_jamendo_genre-discogs-effnet-1.json"),
    "moodtheme": ("mtg_jamendo_moodtheme-discogs-effnet-1.onnx",
                  "mtg_jamendo_moodtheme-discogs-effnet-1.json"),
    "voice": ("voice_instrumental-discogs-effnet-1.onnx",
              "voice_instrumental-discogs-effnet-1.json"),
}
ENCODER = "discogs-effnet-bsdynamic-1.onnx"
POOLING = "patch_f64_arithmetic_mean_v1"
NORMALIZATION = "song_f64_l2_then_cast_f32_v1"
METHODS = ("genre_cosine", "genre_centered_cosine",
           "mood_cosine", "mood_centered_cosine", "embedding_cosine")
RATING_FIELDS = ("genre_similarity_1to5", "mood_energy_similarity_1to5",
                 "timbre_similarity_1to5", "next_track_suitability_1to5")



# Diagnostics deliberately expose only invariant names and numbered cohort
# positions, never private track keys, source paths, notes, or model vectors.
# Only literal allowlisted validation messages may leave the local process.
SAFE_ERRORS = frozenset({
    "Unsafe track identity",
    "Unsafe source-relative track identity",
    "Music source escapes root or is not a file",
    "Existing feature SQLite input is missing",
    "Feature sidecar schema is not v3",
    "Unexpected head, preprocessing or model identity",
    "Invalid track key",
    "Missing/invalid source-audio SHA256",
    "Invalid audio patch count",
    "Invalid classification score shape",
    "Nonfinite/out-of-range classification score",
    "Degenerate Genre/Mood head vector",
    "Voice softmax is not normalized",
    "Invalid stored model metadata",
    "Invalid stored model hashes/classes",
    "Unexpected ONNX filenames or backend deployment hashes",
    "Invalid recorded SHA256",
    "Unexpected native aggregation",
    "Unexpected previous Genre/Mood aggregation",
    "Mixed model definitions within source DB",
    "Duplicate track/head feature row",
    "Must have exactly 100 fully analyzed tracks and exact required heads",
    "Inconsistent source audio or patch count across heads",
    "Incomplete model definitions",
    "Required official ONNX model or class metadata is missing",
    "ONNX weights differ from frozen Rust-v5 cohort",
    "Ordered classification labels differ from baseline",
    "Voice model metadata not valid",
    "Embedding directory does not exist",
    "Embedding folder must contain precisely the same 100 JSON exports",
    "Embedding audio/encoder/patch/frontend identity mismatch",
    "Invalid pooled embedding representation fingerprint",
    "Embedding vector not finite/unit-normalized",
    "Mixed embedding representations",
    "New output directory already exists",
    "Output may not overlap an input or its parent directory",
    "Missing local music root, scanner or trusted native worker",
    "Scanner EXE hash is different from the verified CI binary",
    "Native worker EXE does not match supplied expected SHA256",
    "Original music file no longer matches frozen audio SHA256",
})


class BridgeStageError(Exception):
    def __init__(self, stage: str, source: Exception):
        self.stage = stage
        message = str(source)
        self.reason = message if message in SAFE_ERRORS else type(source).__name__
        super().__init__(f"{stage}: {self.reason}")


def checked_stage(stage: str, func, *args, **kwargs):
    print(f"[CHECK] {stage}", file=sys.stderr, flush=True)
    try:
        result = func(*args, **kwargs)
    except (OSError, ValueError, sqlite3.DatabaseError, KeyError, TypeError,
            AssertionError, UnicodeError) as error:
        raise BridgeStageError(stage, error) from error
    print(f"[PASS] {stage}", file=sys.stderr, flush=True)
    return result


def check_audio_sources(tracks: dict, root: Path) -> None:
    for number, key in enumerate(sorted(tracks), 1):
        # One numeric index is actionable for local diagnostics without
        # disclosing the private file key in command output.
        def check_one():
            source = safe_song_path(key, root)
            if digest(source) != tracks[key]["genre"]["audio_sha256"]:
                raise ValueError("Original music file no longer matches frozen audio SHA256")
        checked_stage(f"audio_sha256_{number:03d}_of_100", check_one)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def safe_song_path(key: str, root: Path) -> Path:
    if not isinstance(key, str) or not key or "\\" in key or "\x00" in key:
        raise ValueError("Unsafe track identity")
    parts = key.split("/")
    if (any(p in ("", ".", "..") or ":" in p or "\n" in p or "\r" in p for p in parts)
            or PurePosixPath(key).is_absolute()):
        raise ValueError("Unsafe source-relative track identity")
    source = root.joinpath(*parts).resolve(strict=True)
    if not source.is_relative_to(root.resolve(strict=True)) or not source.is_file():
        raise ValueError("Music source escapes root or is not a file")
    return source


def open_readonly(db: Path):
    if not db.is_file():
        raise ValueError("Existing feature SQLite input is missing")
    return sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)


def read_cohort(db: Path, heads: set[str], expected_frontend: str) -> tuple[dict, dict]:
    """Require exactly 100 distinct keys and precisely the required heads per key."""
    with closing(open_readonly(db)) as c:
        if c.execute("PRAGMA user_version").fetchone()[0] != 3:
            raise ValueError("Feature sidecar schema is not v3")
        data = c.execute("""
            SELECT t.track_file, t.model_id, t.audio_sha256,
                   t.patches_analyzed, t.scores_f32_le, t.model_key,
                   m.preprocessing_version, m.embedding_model,
                   m.classification_model, m.models_sha256_json,
                   m.classes_json, m.aggregation
            FROM feature_tracks AS t
            JOIN feature_models AS m ON t.model_key=m.model_key
            ORDER BY t.track_file, t.model_id
        """).fetchall()
    tracks: dict[str, dict] = {}
    definitions: dict[str, tuple] = {}
    for key, head, audio, patches, blob, model_key, frontend, encoder, classifier, raw_sha, labels_json, aggregation in data:
        if head not in heads or frontend != expected_frontend or not model_key:
            raise ValueError("Unexpected head, preprocessing or model identity")
        if not isinstance(key, str) or not key:
            raise ValueError("Invalid track key")
        if (not isinstance(audio, str) or len(audio) != 64
                or any(ch not in "0123456789abcdefABCDEF" for ch in audio)):
            raise ValueError("Missing/invalid source-audio SHA256")
        if not isinstance(patches, int) or patches <= 0:
            raise ValueError("Invalid audio patch count")
        if not isinstance(blob, bytes) or len(blob) != 4 * DIMENSIONS[head]:
            raise ValueError("Invalid classification score shape")
        vector = struct.unpack("<" + "f" * DIMENSIONS[head], blob)
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in vector):
            raise ValueError("Nonfinite/out-of-range classification score")
        if (head != "voice"
                and statistics.pvariance(vector) <= 1e-10):
            raise ValueError("Degenerate Genre/Mood head vector")
        if head == "voice" and abs(sum(vector) - 1) > 0.001:
            raise ValueError("Voice softmax is not normalized")
        try:
            hashes, labels = json.loads(raw_sha), json.loads(labels_json)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid stored model metadata") from exc
        if (not isinstance(hashes, dict) or not isinstance(labels, list)
                or len(labels) != DIMENSIONS[head]
                or not all(isinstance(label, str) and label for label in labels)
                or len(set(labels)) != len(labels)):
            raise ValueError("Invalid stored model hashes/classes")
        expected_hash_keys = {encoder, classifier}
        extra = set(hashes) - expected_hash_keys
        if (encoder != ENCODER or classifier != EXPECTED_MODELS[head][0]
                or not expected_hash_keys <= set(hashes)
                or (extra if expected_frontend == OLD_FRONTEND
                    else extra - {
                        "essentia_cpp_worker_binary_sha256",
                        "essentia_cpp_native_deployment_manifest_sha256"
                    })
                or (expected_frontend != OLD_FRONTEND
                    and "essentia_cpp_worker_binary_sha256" not in hashes)):
            raise ValueError("Unexpected ONNX filenames or backend deployment hashes")
        if any(not isinstance(x, str) or len(x) != 64 or
               any(c not in "0123456789abcdefABCDEF" for c in x)
               for x in hashes.values()):
            raise ValueError("Invalid recorded SHA256")
        if expected_frontend != OLD_FRONTEND:
            if aggregation != ("arithmetic_mean_of_per_patch_softmax_scores"
                               if head == "voice"
                               else "arithmetic_mean_of_per_patch_sigmoid_scores"):
                raise ValueError("Unexpected native aggregation")
        else:
            if aggregation != "arithmetic_mean_of_per_patch_sigmoid_scores":
                raise ValueError("Unexpected previous Genre/Mood aggregation")
        definition = (encoder, classifier, hashes[encoder].lower(),
                      hashes[classifier].lower(), tuple(labels), aggregation)
        if head in definitions and definitions[head] != definition:
            raise ValueError("Mixed model definitions within source DB")
        definitions[head] = definition
        row = tracks.setdefault(key, {})
        if head in row:
            raise ValueError("Duplicate track/head feature row")
        row[head] = {"audio_sha256": audio.lower(), "patches": patches,
                     "scores": vector, "model_key": model_key,
                     "preprocessing": frontend, "hashes": hashes}
    if len(tracks) != N or any(set(rows) != heads for rows in tracks.values()):
        raise ValueError("Must have exactly 100 fully analyzed tracks and exact required heads")
    for row in tracks.values():
        if (len({v["audio_sha256"] for v in row.values()}) != 1
                or len({v["patches"] for v in row.values()}) != 1):
            raise ValueError("Inconsistent source audio or patch count across heads")
    if set(definitions) != heads:
        raise ValueError("Incomplete model definitions")
    return tracks, definitions


def validate_model_files(models: Path, definitions: dict) -> dict[str, str]:
    files = {ENCODER}
    for head in DIMENSIONS:
        files.update(EXPECTED_MODELS[head])
    digests = {}
    for name in sorted(files):
        path = models / name
        if not path.is_file():
            raise ValueError("Required official ONNX model or class metadata is missing")
        digests[name] = digest(path)
    for head in ("genre", "moodtheme"):
        encoder, classifier, encoder_sha, classifier_sha, labels, _ = definitions[head]
        if digests[encoder] != encoder_sha or digests[classifier] != classifier_sha:
            raise ValueError("ONNX weights differ from frozen Rust-v5 cohort")
        metadata = json.loads((models / EXPECTED_MODELS[head][1]).read_text(encoding="utf-8-sig"))
        if metadata.get("classes") != list(labels):
            raise ValueError("Ordered classification labels differ from baseline")
    voice_labels = json.loads((models / EXPECTED_MODELS["voice"][1]).read_text(encoding="utf-8-sig"))
    if (not isinstance(voice_labels.get("classes"), list)
            or len(voice_labels["classes"]) != DIMENSIONS["voice"]):
        raise ValueError("Voice model metadata not valid")
    return digests


def embedding_filename(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"


def validate_embeddings(directory: Path, tracks: dict, definitions: dict) -> dict[str, tuple]:
    if not directory.is_dir():
        raise ValueError("Embedding directory does not exist")
    expected_files = {embedding_filename(key) for key in tracks}
    present = {f.name for f in directory.iterdir() if f.is_file()}
    if expected_files != present:
        raise ValueError("Embedding folder must contain precisely the same 100 JSON exports")
    vectors = {}
    fingerprints = set()
    preprocessing = next(iter(tracks.values()))["genre"]["preprocessing"]
    encoder_sha = definitions["genre"][2]
    for key in sorted(tracks):
        payload = json.loads((directory / embedding_filename(key)).read_text(encoding="utf-8-sig"))
        main = tracks[key]["genre"]
        expected = {
            "schema_version": 1, "kind": "discogs_effnet_song_embedding",
            "validation_status": "experimental_unvalidated",
            "dimension": 1280, "track_file": key,
            "audio_sha256": main["audio_sha256"],
            "patches_analyzed": main["patches"],
            "encoder_model": ENCODER, "encoder_sha256": encoder_sha,
            "preprocessing_version": preprocessing,
            "pooling_version": POOLING,
            "normalization_version": NORMALIZATION,
        }
        if any(payload.get(field) != value for field, value in expected.items()):
            raise ValueError("Embedding audio/encoder/patch/frontend identity mismatch")
        contract = [1, ENCODER, encoder_sha, preprocessing, POOLING, NORMALIZATION, 1280]
        expected_fp = hashlib.sha256(json.dumps(
            contract, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        if payload.get("representation_fingerprint") != expected_fp:
            raise ValueError("Invalid pooled embedding representation fingerprint")
        fingerprints.add(expected_fp)
        v = payload.get("vector_f32")
        if (not isinstance(v, list) or len(v) != 1280
                or any(isinstance(x, bool) or not isinstance(x, (float, int))
                       or not math.isfinite(x) for x in v)
                or abs(math.sqrt(sum(float(x) * float(x) for x in v)) - 1) >= 1e-5):
            raise ValueError("Embedding vector not finite/unit-normalized")
        vectors[key] = tuple(float(x) for x in v)
    if len(fingerprints) != 1:
        raise ValueError("Mixed embedding representations")
    return vectors


def verify_disjoint_output(out: Path, inputs: list[Path]) -> None:
    target = out.resolve()
    if out.exists():
        raise FileExistsError("New output directory already exists")
    for raw in inputs:
        root = raw.resolve()
        if target == root or target.is_relative_to(root) or root.is_relative_to(target):
            raise ValueError("Output may not overlap an input or its parent directory")


def prepare(args) -> dict:
    tracks, definitions = checked_stage(
        "baseline_feature_cohort", read_cohort,
        args.baseline_db, {"genre", "moodtheme"}, OLD_FRONTEND)
    old_vectors = checked_stage(
        "baseline_embedding_exports", validate_embeddings,
        args.baseline_embeddings, tracks, definitions)
    hashes = checked_stage(
        "onnx_model_weights_and_class_metadata", validate_model_files,
        args.models_dir, definitions)

    def verify_binaries():
        if not args.audio_root.is_dir() or not args.scanner.is_file() or not args.worker.is_file():
            raise ValueError("Missing local music root, scanner or trusted native worker")
        scanner_hash = digest(args.scanner)
        if scanner_hash != args.expected_scanner_sha256.lower():
            raise ValueError("Scanner EXE hash is different from the verified CI binary")
        worker_hash = digest(args.worker)
        if args.expected_worker_sha256 and worker_hash != args.expected_worker_sha256.lower():
            raise ValueError("Native worker EXE does not match supplied expected SHA256")
        return scanner_hash, worker_hash

    scanner_hash, worker_hash = checked_stage(
        "verified_scanner_and_native_worker", verify_binaries)
    # Verify all 100 original music files before writing any manifest.
    check_audio_sources(tracks, args.audio_root)
    assert len(old_vectors) == N
    manifest = "".join(k + "\n" for k in sorted(tracks)).encode("utf-8")
    before = digest(args.baseline_db)
    output = args.out_dir
    checked_stage("new_output_directory_safety", verify_disjoint_output,
                  output, [args.baseline_db, args.baseline_embeddings,
                           args.audio_root, args.models_dir,
                           args.scanner, args.worker])
    provenance = {
        "schema": "native_similarity_cohort_bridge_v1",
        "status": "PREFLIGHT_VERIFIED_NO_NATIVE_SCAN_YET",
        "tracks": N,
        "heads_old": ["genre", "moodtheme"],
        "heads_native_expected": ["genre", "moodtheme", "voice"],
        "source_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "old_sqlite_sha256": before,
        "old_embedding_fingerprint": hashlib.sha256(json.dumps([
            1, ENCODER, definitions["genre"][2], OLD_FRONTEND,
            POOLING, NORMALIZATION, 1280
        ], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "verified_scanner_exe_sha256": scanner_hash,
        "native_worker_exe_sha256": worker_hash,
        "model_file_sha256": hashes,
        "notes": [
            "Source audio 100/100 SHA256 verified before manifest creation",
            "Original listening CSV and local vectors remain untouched",
            "Same 100 keys as exact legacy schema-v3 cohort; no random re-selection",
            "Experimental research only; no native dependency distribution approval",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "native-embeddings").mkdir()
    (output / "exact-100-tracks.txt").write_bytes(manifest)
    (output / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return provenance


def cos(a: tuple, b: tuple, centered: bool = False) -> float:
    if centered:
        x, y = statistics.fmean(a), statistics.fmean(b)
        a, b = (v-x for v in a), (v-y for v in b)
    pairs = list(zip(a, b))
    numerator = sum(x*y for x, y in pairs)
    den = math.sqrt(sum(x*x for x, y in pairs) * sum(y*y for x, y in pairs))
    if den <= 1e-12:
        raise ValueError("Undefined vector cosine")
    return numerator / den


def average_ranks(values: list[float]) -> list[float]:
    indices = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indices):
        end = start + 1
        while end < len(indices) and values[indices[end]] == values[indices[start]]:
            end += 1
        r = (start + end - 1) / 2
        for j in range(start, end):
            ranks[indices[j]] = r
        start = end
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    x, y = average_ranks(a), average_ranks(b)
    mx, my = statistics.fmean(x), statistics.fmean(y)
    den = math.sqrt(sum((v-mx)**2 for v in x) * sum((v-my)**2 for v in y))
    if den == 0:
        raise ValueError("Constant song-pair score ranking")
    return sum((v-mx)*(w-my) for v, w in zip(x, y)) / den


def model_scores(left: dict, right: dict) -> dict[str, float]:
    return {
        "genre_cosine": cos(left["genre"], right["genre"]),
        "genre_centered_cosine": cos(left["genre"], right["genre"], True),
        "mood_cosine": cos(left["moodtheme"], right["moodtheme"]),
        "mood_centered_cosine": cos(left["moodtheme"], right["moodtheme"], True),
        "embedding_cosine": cos(left["embedding"], right["embedding"]),
    }



def compare_frozen_human_pilot(ratings: Path, sealed_audit: Path,
                              old_tracks: dict, new_tracks: dict) -> dict:
    """Read human ratings and original model-selected scores; never modify either."""
    raw = ratings.read_bytes()
    try:
        contents = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        contents = raw.decode("cp1252")
    heading = contents.splitlines()[0]
    delimiter = max((",", ";", "\t"), key=heading.count)
    if not heading.count(delimiter):
        raise ValueError("Unrecognized listening CSV delimiter")
    with io.StringIO(contents, newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        expected_fields = ("left", "right", *RATING_FIELDS, "confidence_1to3", "notes")
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError("Original listening CSV header differs")
        rows = list(reader)
    sealed = json.loads(sealed_audit.read_text(encoding="utf-8-sig"))
    if sealed.get("schema") != "private_blinded_local_ab_pilot_selection_v1":
        raise ValueError("Unexpected original model-score audit")
    pairs = sealed.get("pairs_private_do_not_open_before_review")
    if len(rows) != 12 or not isinstance(pairs, list) or len(pairs) != 12:
        raise ValueError("Expected exactly 12 human-rated/audited pilot pairs")
    pairs_old, pairs_new = [], []
    human = []
    for idx, (row, item) in enumerate(zip(rows, pairs), 1):
        a, b = row.get("left"), row.get("right")
        if (item.get("pair_number") != idx or item.get("left") != a
                or item.get("right") != b or a not in old_tracks
                or b not in old_tracks or a == b):
            raise ValueError("Sealed pilot pairing/order does not match exact 100-song cohort")
        manual = []
        for field in RATING_FIELDS:
            value = row.get(field)
            if value not in ("1", "2", "3", "4", "5"):
                raise ValueError("Invalid or incomplete human rating")
            manual.append(int(value))
        if row.get("confidence_1to3") not in ("1", "2", "3"):
            raise ValueError("Invalid human confidence")
        human.append(manual)
        original = model_scores(old_tracks[a], old_tracks[b])
        prior = item.get("similarity_scores_not_probabilities")
        if not isinstance(prior, dict) or set(prior) != set(METHODS):
            raise ValueError("Sealed pilot missing original five model scores")
        for name in METHODS:
            previous = prior[name]
            if (not isinstance(previous, (float, int)) or isinstance(previous, bool)
                    or not math.isfinite(previous) or abs(original[name] - previous) > 1e-6):
                raise ValueError("Old cohort does not reproduce the originally sealed pilot scores")
        pairs_old.append(original)
        pairs_new.append(model_scores(new_tracks[a], new_tracks[b]))
    samples = {}
    for name, selection in (("all_12", list(range(12))),
                            ("music_11_excluding_spoken_pair_10",
                             [i for i in range(12) if i != 9])):
        by_method = {}
        for method in METHODS:
            by_method[method] = {}
            for j, field in enumerate(RATING_FIELDS):
                y = [human[i][j] for i in selection]
                x_old = [pairs_old[i][method] for i in selection]
                x_new = [pairs_new[i][method] for i in selection]
                # A deliberately synthetic/all-tied pilot can have no rank
                # information; report null instead of falsely assigning 0.
                try:
                    old_rho = round(spearman(x_old, y), 6)
                except ValueError:
                    old_rho = None
                try:
                    native_rho = round(spearman(x_new, y), 6)
                except ValueError:
                    native_rho = None
                by_method[method][field] = {
                    "previous_spearman": old_rho,
                    "native_spearman": native_rho,
                }
        samples[name] = by_method
    return {
        "status": "EXPLORATORY_ONLY_NO_METRIC_WINNER",
        "sample_sizes": {"all": 12, "music": 11},
        "human_ratings_verified_from_local_csv": True,
        "original_sealed_scores_reproduced": True,
        "nonmusic_pair": 10,
        "paired_model_vs_human": samples,
        "caution": "Same nonrandom 12 labels used before; not independent validation or personal training",
    }



def compare(args) -> dict:
    plan_path = args.plan_dir / "provenance.json"
    manifest_path = args.plan_dir / "exact-100-tracks.txt"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != "native_similarity_cohort_bridge_v1":
        raise ValueError("Wrong frozen manifest/provenance schema")
    if digest(manifest_path) != plan["source_manifest_sha256"]:
        raise ValueError("Original frozen manifest has changed")
    if digest(args.baseline_db) != plan["old_sqlite_sha256"]:
        raise ValueError("Original v5 feature DB drifted after prepare")
    old, old_def = read_cohort(args.baseline_db, {"genre", "moodtheme"}, OLD_FRONTEND)
    if hashlib.sha256("".join(k+"\n" for k in sorted(old)).encode()).hexdigest() != plan["source_manifest_sha256"]:
        raise ValueError("Frozen 100 source keys changed")
    previous = validate_embeddings(args.baseline_embeddings, old, old_def)
    native, new_def = read_cohort(
        args.native_db, {"genre", "moodtheme", "voice"}, args.native_frontend)
    if not args.native_frontend.startswith(NATIVE_PREFIX):
        raise ValueError("Native preprocessing version must be exact C++ frontend")
    if set(native) != set(old):
        raise ValueError("Native run does not contain the same exact 100 tracks")
    if new_def["genre"] != old_def["genre"] or new_def["moodtheme"] != old_def["moodtheme"]:
        raise ValueError("ONNX weights, class ordering or aggregation changed")
    if (new_def["voice"][2] != old_def["genre"][2]
            or new_def["voice"][3] != plan["model_file_sha256"][EXPECTED_MODELS["voice"][0]]):
        raise ValueError("Voice/encoder model identity invalid")
    if new_def["voice"][4] != tuple(json.loads(
            (args.models_dir / EXPECTED_MODELS["voice"][1]).read_text(encoding="utf-8-sig")
        )["classes"]):
        raise ValueError("Voice class labels mismatch")
    for key in sorted(old):
        for head in ("genre", "moodtheme"):
            a, b = old[key][head], native[key][head]
            if a["audio_sha256"] != b["audio_sha256"] or a["patches"] != b["patches"]:
                raise ValueError("Audio SHA256 or patch counts mismatch")
            if a["model_key"] == b["model_key"]:
                raise ValueError("Native and Rust-v5 cache identities must differ")
        voice = native[key]["voice"]
        if voice["audio_sha256"] != old[key]["genre"]["audio_sha256"] or voice["patches"] != old[key]["genre"]["patches"]:
            raise ValueError("Voice source audio or patch counts differ")
        if voice["hashes"].get("essentia_cpp_worker_binary_sha256") != plan["native_worker_exe_sha256"]:
            raise ValueError("Native worker fingerprint changed after preflight")
    for filename, expected in plan["model_file_sha256"].items():
        if digest(args.models_dir / filename) != expected:
            raise ValueError("Model weight/class file changed since preflight")
    now = validate_embeddings(args.native_embeddings, native, new_def)
    score_diffs = {head: [] for head in ("genre", "moodtheme")}
    emb_cos = []
    emb_abs = []
    for key in sorted(old):
        for head in score_diffs:
            score_diffs[head].extend(
                abs(x-y) for x, y in zip(old[key][head]["scores"], native[key][head]["scores"])
            )
        emb_cos.append(cos(previous[key], now[key]))
        emb_abs.append(max(abs(x-y) for x, y in zip(previous[key], now[key])))
    keys = sorted(old)
    baseline = {
        key: {"genre": old[key]["genre"]["scores"],
              "moodtheme": old[key]["moodtheme"]["scores"],
              "embedding": previous[key]} for key in keys
    }
    new_data = {
        key: {"genre": native[key]["genre"]["scores"],
              "moodtheme": native[key]["moodtheme"]["scores"],
              "embedding": now[key]} for key in keys
    }
    old_scores, new_scores = {m: [] for m in METHODS}, {m: [] for m in METHODS}
    for a, b in itertools.combinations(keys, 2):
        x, y = model_scores(baseline[a], baseline[b]), model_scores(new_data[a], new_data[b])
        for m in METHODS:
            old_scores[m].append(x[m])
            new_scores[m].append(y[m])
    ranking = {
        name: {
            "spearman_all_4950_pairs": round(spearman(old_scores[name], new_scores[name]), 8),
            "max_absolute_similarity_change": round(
                max(abs(x-y) for x, y in zip(old_scores[name], new_scores[name])), 8),
        } for name in METHODS
    }
    max_score = max(max(diffs) for diffs in score_diffs.values())
    min_cos = min(emb_cos)
    passed = max_score <= args.score_tolerance and min_cos >= args.embedding_cosine_min
    report = {
        "schema": "native_similarity_cohort_comparison_v1",
        "status": "PASS_EXPLORATORY_TOLERANCES" if passed else "REVIEW_NUMERICAL_DRIFT",
        "track_count": N, "complete_song_pairs": N*(N-1)//2,
        "frozen_manifest_sha256": plan["source_manifest_sha256"],
        "old_sqlite_sha256_unchanged": digest(args.baseline_db) == plan["old_sqlite_sha256"],
        "native_sqlite_sha256": digest(args.native_db),
        "verified_scanner_sha256": plan["verified_scanner_exe_sha256"],
        "verified_native_worker_sha256": plan["native_worker_exe_sha256"],
        "model_file_sha256": plan["model_file_sha256"],
        "old_backend": OLD_FRONTEND,
        "native_backend": args.native_frontend,
        "audio_sha256_matches": N,
        "patch_counts_match": N,
        "voice_head_coverage": N,
        "classification_max_abs_diff": {
            k: round(max(v), 9) for k, v in score_diffs.items()},
        "classification_mean_abs_diff": {
            k: round(statistics.fmean(v), 9) for k, v in score_diffs.items()},
        "overall_max_abs_score_difference": round(max_score, 9),
        "per_song_embedding_cosine_min": round(min_cos, 9),
        "per_song_embedding_cosine_mean": round(statistics.fmean(emb_cos), 9),
        "per_song_embedding_max_abs_component_difference": round(max(emb_abs), 9),
        "exploratory_score_tolerance": args.score_tolerance,
        "exploratory_min_embedding_cosine": args.embedding_cosine_min,
        "similarity_rank_drift": ranking,
        "warning": ("Paired comparison is NOT independently certified numerical Essentia parity. "
                    "4950 pairs share just 100 songs and are not independent human labels. "
                    "Do not select general or personal fusion weights from the 12-pair pilot."),
    }
    if (args.ratings is None) != (args.pilot_audit is None):
        raise ValueError("Both the original pilot ratings and sealed audit are required together")
    if args.ratings is not None:
        report["original_12_pair_human_sensitivity"] = compare_frozen_human_pilot(
            args.ratings, args.pilot_audit, baseline, new_data)
    verify_disjoint_output(args.out_dir, [args.plan_dir, args.baseline_db,
                                           args.baseline_embeddings,
                                           args.native_db, args.native_embeddings,
                                           args.models_dir])
    args.out_dir.mkdir(parents=True, exist_ok=False)
    (args.out_dir / "aggregate-native-cohort-comparison.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Freeze old 100 exactly, verify files, then create NEW private scan plan")
    prep.add_argument("--baseline-db", required=True, type=Path)
    prep.add_argument("--baseline-embeddings", required=True, type=Path)
    prep.add_argument("--audio-root", required=True, type=Path)
    prep.add_argument("--models-dir", required=True, type=Path)
    prep.add_argument("--scanner", required=True, type=Path)
    prep.add_argument("--worker", required=True, type=Path)
    prep.add_argument("--expected-scanner-sha256", required=True)
    prep.add_argument("--expected-worker-sha256", default="")
    prep.add_argument("--out-dir", required=True, type=Path)
    comp = sub.add_parser("compare", help="Analyze already produced native outputs, never start a scanner")
    comp.add_argument("--plan-dir", required=True, type=Path)
    comp.add_argument("--baseline-db", required=True, type=Path)
    comp.add_argument("--baseline-embeddings", required=True, type=Path)
    comp.add_argument("--native-db", required=True, type=Path)
    comp.add_argument("--native-embeddings", required=True, type=Path)
    comp.add_argument("--models-dir", required=True, type=Path)
    comp.add_argument("--native-frontend", required=True)
    comp.add_argument("--ratings", type=Path, help="Optional completed original 12-pair CSV; read-only")
    comp.add_argument("--pilot-audit", type=Path, help="Optional original sealed audit; read-only")
    comp.add_argument("--score-tolerance", type=float, default=0.001)
    comp.add_argument("--embedding-cosine-min", type=float, default=0.999)
    comp.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "compare" and not (0 < args.score_tolerance <= 0.1
                                              and 0 < args.embedding_cosine_min <= 1):
            raise ValueError("Invalid exploratory tolerance")
        report = prepare(args) if args.action == "prepare" else compare(args)
        # No source paths/song titles or raw vectors are printed.
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except BridgeStageError as error:
        parser.exit(2, f"Native cohort bridge failed at {error.stage}: {error.reason}\n")
    except (OSError, ValueError, sqlite3.DatabaseError, KeyError, TypeError,
            AssertionError, UnicodeError) as error:
        # Do not print the private source path in unclassified exceptions.
        reason = str(error) if str(error) in SAFE_ERRORS else type(error).__name__
        parser.exit(2, "Native cohort bridge stopped safely: " + reason + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
