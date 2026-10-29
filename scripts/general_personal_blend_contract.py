#!/usr/bin/env python3
"""WP2-P0: synthetic General/Personal score-batch and legacy Bliss 23D contracts.

No personal training, scores, local user files, app integration or vote collection.
The caller must separately validate any calibrator: common contract IDs alone
do not prove statistical calibration or musical quality. Fail closed per QUERY.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

DIMENSIONS = 23
LEGACY_MATRIX_FORMAT = 1


@dataclass(frozen=True)
class PersonalEvidence:
    """A proposed, already independently validated per-user score result."""
    profile_id: str
    feature_fingerprint: str
    score_calibration_id: str
    candidate_cohort_fingerprint: str
    version: int
    quality_validated: bool
    calibration_validated: bool
    scores: tuple[float, ...]


@dataclass(frozen=True)
class BlendResult:
    scores: tuple[float, ...]
    requested_personal_percent: int
    effective_personal_percent: int
    fallback_reason: str


def valid_scores(scores: object, *, expected: int | None = None) -> bool:
    if not isinstance(scores, (tuple, list)):
        return False
    if expected is not None and len(scores) != expected:
        return False
    return len(scores) > 0 and all(
        type(value) in (int, float) and math.isfinite(value)
        and 0.0 <= value <= 1.0 for value in scores
    )


def choose_scores(
    general: tuple[float, ...],
    *,
    requested_personal_percent: int,
    expected_profile: str,
    expected_feature_fingerprint: str,
    expected_score_calibration_id: str,
    expected_candidate_cohort_fingerprint: str,
    personal: PersonalEvidence | None = None,
) -> BlendResult:
    """Query-wide fallback; no partial personalized ranks or implicit training.

    General and Personal MUST have already passed independently certified
    calibration to the same scale; this code checks compatibility flags/IDs
    and gates only. No personal score fits are performed on the query.
    """
    if not valid_scores(general):
        raise ValueError("A complete, finite, bounded General score batch is mandatory")
    if type(requested_personal_percent) is not int or not (
            0 <= requested_personal_percent <= 100):
        raise ValueError("Personal influence must be an integer 0..100")
    for value in (
        expected_profile, expected_feature_fingerprint,
        expected_score_calibration_id, expected_candidate_cohort_fingerprint,
    ):
        if not isinstance(value, str) or not value:
            raise ValueError("Missing pinned profile/representation/calibration/cohort identity")
    base = tuple(general)
    def fallback(reason: str) -> BlendResult:
        return BlendResult(base, requested_personal_percent, 0, reason)

    if requested_personal_percent == 0:
        return fallback("personal_disabled_by_requested_zero_percent")
    if personal is None:
        return fallback("no_personal_model")
    if type(personal) is not PersonalEvidence:
        return fallback("malformed_personal_evidence")
    if personal.version != 1 or not personal.quality_validated:
        return fallback("personal_quality_gate_not_passed")
    if not personal.calibration_validated:
        return fallback("personal_calibration_gate_not_passed")
    if personal.profile_id != expected_profile:
        return fallback("wrong_personal_profile")
    if personal.feature_fingerprint != expected_feature_fingerprint:
        return fallback("feature_fingerprint_mismatch")
    if personal.score_calibration_id != expected_score_calibration_id:
        return fallback("score_calibration_contract_mismatch")
    if personal.candidate_cohort_fingerprint != expected_candidate_cohort_fingerprint:
        return fallback("candidate_cohort_mismatch")
    if not valid_scores(personal.scores, expected=len(base)):
        return fallback("incomplete_or_invalid_personal_scores")

    alpha = requested_personal_percent / 100.0
    if alpha == 1.0:
        result = tuple(personal.scores)
    else:
        result = tuple(
            (1.0 - alpha) * g + alpha * p for g, p in zip(base, personal.scores)
        )
    if not valid_scores(result, expected=len(base)):
        return fallback("invalid_mixed_scores")
    return BlendResult(result, requested_personal_percent,
                       requested_personal_percent, "none")


def inspect_legacy_bliss_matrix(data: object) -> dict:
    """Only check the old bliss-learner JSON format, not suitability for use.

    Source: chrober/bliss-learner src/main.rs -> {"m":{"v":1,"dim":[23,23],
    "data": [529 finite scalar values]}}. Full PSD, numerical conditioning,
    exact feature scale and independent held-out benefit are NOT certified.
    """
    valid = False
    if isinstance(data, dict) and isinstance(data.get("m"), dict):
        matrix = data["m"]
        values = matrix.get("data")
        valid = (
            type(matrix.get("v")) is int and matrix["v"] == LEGACY_MATRIX_FORMAT
            and matrix.get("dim") == [DIMENSIONS, DIMENSIONS]
            and isinstance(values, list) and len(values) == DIMENSIONS ** 2
            and all(type(value) in (int, float) and math.isfinite(value)
                    for value in values)
        )
    return {
        "format": "bliss_learner_legacy_23x23_mahalanobis_v1",
        "structurally_compatible": bool(valid),
        "positive_semidefinite_certified": False,
        "feature_order_and_scale_certified": False,
        "personal_model_quality_certified": False,
        "general_personal_score_calibration_certified": False,
        "may_activate_general_personal_blend": False,
    }


def legacy_triplet_counts(records: object) -> dict:
    """Inspect existing Lab triples without exposing track names or mutating.

    Existing Lab order is [similar_1, similar_2, odd]; this does not establish
    an independent personal holdout, sample selection policy or consent.
    """
    if not isinstance(records, list):
        raise ValueError("Legacy training format requires a list")
    valid = 0
    invalid = 0
    duplicate = 0
    seen = set()
    for item in records:
        if not isinstance(item, list) or len(item) != 3 or not all(
                isinstance(x, str) and bool(x) and "\0" not in x for x in item):
            invalid += 1
            continue
        if len(set(item)) != 3:
            invalid += 1
            continue
        # Similar-pair swap is not a new independent judgment.
        identity = (tuple(sorted(item[:2])), item[2])
        if identity in seen:
            duplicate += 1
        else:
            seen.add(identity)
            valid += 1
    return {
        "schema": "legacy_blissmixerlab_triplet_shape_aggregate_v1",
        "valid_unique_ordered_role_triplets": valid,
        "invalid_triplets": invalid,
        "duplicate_triplets": duplicate,
        "does_not_certify_artist_album_disjointness": True,
        "does_not_count_user_survey_as_new_required_test": True,
    }
