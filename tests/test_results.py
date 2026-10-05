"""Contract tests for the additive structured result layer."""

import cv2
import numpy as np
import pytest

from pyxelator import (
    ActionResult,
    MatchCandidate,
    MatchResult,
    Rectangle,
    VerificationResult,
    check_image_exists,
    find_image_in_screenshot,
    match_result,
)


def _encode(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


@pytest.fixture
def matching_images(tmp_path):
    rng = np.random.default_rng(12)
    template = rng.integers(0, 256, size=(20, 30, 3), dtype=np.uint8)
    screenshot = np.full((100, 140, 3), 240, dtype=np.uint8)
    screenshot[40:60, 70:100] = template
    path = tmp_path / "target.png"
    cv2.imwrite(str(path), template)
    return _encode(screenshot), str(path)


@pytest.fixture
def ambiguous_images(tmp_path):
    rng = np.random.default_rng(34)
    template = rng.integers(0, 256, size=(20, 30, 3), dtype=np.uint8)
    screenshot = np.full((100, 160, 3), 240, dtype=np.uint8)
    screenshot[20:40, 15:45] = template
    screenshot[60:80, 110:140] = template
    path = tmp_path / "repeated-target.png"
    cv2.imwrite(str(path), template)
    return _encode(screenshot), str(path)


def test_match_result_reports_success_evidence(matching_images):
    screenshot, template = matching_images

    result = match_result(screenshot, template)

    assert isinstance(result, MatchResult)
    assert result.ok is True
    assert result.found is True
    assert bool(result) is True
    assert result.score == pytest.approx(1.0, abs=1e-3)
    assert result.threshold == 0.7
    assert result.location == Rectangle(x=70, y=40, width=30, height=20)
    assert result.coordinates == (85, 50)
    assert result.scale == 1.0
    assert result.ambiguous is False
    assert result.reason is None
    assert isinstance(result.candidates[0], MatchCandidate)
    assert result.candidates[0].coordinates == (85, 50)


def test_match_result_rejects_equally_strong_distinct_candidates(ambiguous_images):
    screenshot, template = ambiguous_images

    result = match_result(screenshot, template)

    assert result.ok is False
    assert result.found is True
    assert bool(result) is False
    assert result.ambiguous is True
    assert result.reason == "ambiguous_match"
    assert len(result.candidates) >= 2
    assert result.candidates[0].score == pytest.approx(1.0, abs=1e-3)
    assert result.candidates[1].score == pytest.approx(1.0, abs=1e-3)
    assert result.score_margin == pytest.approx(0.0, abs=1e-6)
    assert {candidate.coordinates for candidate in result.candidates[:2]} == {
        (30, 30),
        (125, 70),
    }


def test_below_threshold_result_keeps_rejected_candidate_evidence(matching_images):
    screenshot, template = matching_images

    result = match_result(screenshot, template, confidence=1.1)

    assert result.ok is False
    assert result.found is False
    assert bool(result) is False
    assert result.reason == "below_threshold"
    assert result.score == pytest.approx(1.0, abs=1e-3)
    assert result.location is not None
    assert result.coordinates == (85, 50)
    assert result.scale == 1.0


def test_invalid_screenshot_has_machine_readable_reason(matching_images):
    _, template = matching_images

    result = match_result(b"not an image", template)

    assert result.reason == "invalid_screenshot"
    assert result.score is None
    assert result.location is None


def test_invalid_and_flat_templates_have_distinct_reasons(tmp_path, matching_images):
    screenshot, _ = matching_images
    missing = tmp_path / "missing.png"
    flat = tmp_path / "flat.png"
    cv2.imwrite(str(flat), np.full((20, 20, 3), 100, dtype=np.uint8))

    assert match_result(screenshot, str(missing)).reason == "invalid_template"
    assert match_result(screenshot, str(flat)).reason == "flat_template"


def test_legacy_matching_functions_keep_v05_return_types(matching_images):
    screenshot, template = matching_images

    coordinates = find_image_in_screenshot(screenshot, template)
    exists = check_image_exists(screenshot, template)

    assert type(coordinates) is tuple
    assert coordinates == (85, 50)
    assert type(exists) is bool
    assert exists is True


def test_legacy_matching_remains_compatible_for_ambiguous_images(ambiguous_images):
    screenshot, template = ambiguous_images

    coordinates = find_image_in_screenshot(screenshot, template)
    exists = check_image_exists(screenshot, template)

    assert type(coordinates) is tuple
    assert coordinates in {(30, 30), (125, 70)}
    assert type(exists) is bool
    assert exists is True


def test_action_and_verification_results_are_truthy_only_on_success(matching_images):
    screenshot, template = matching_images
    match = match_result(screenshot, template)
    verification = VerificationResult(
        ok=True,
        expected_visible=True,
        observed_visible=True,
        match=match,
    )
    success = ActionResult(
        ok=True,
        action="click",
        match=match,
        verification=verification,
        artifacts=("before.png", "after.png"),
    )
    failure = ActionResult(ok=False, action="click", match=match, reason="click_failed")

    assert bool(verification) is True
    assert bool(success) is True
    assert success.failure is None
    assert bool(failure) is False
    assert failure.failure == "click_failed"
