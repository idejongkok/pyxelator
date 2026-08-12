"""
Unit tests for the core template matching logic.

These tests are pure OpenCV - no browser, no driver, no network. Screenshots
and templates are synthesised as numpy arrays so every case is deterministic.
"""

import cv2
import numpy as np
import pytest

from pyxelator.core import (
    _best_match,
    check_image_exists,
    find_image_in_screenshot,
    locate_match,
    match_score,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 400, 300
BUTTON_W, BUTTON_H = 60, 24
BUTTON_X, BUTTON_Y = 250, 180


def _encode(img: np.ndarray) -> bytes:
    """Encode a BGR numpy image to PNG bytes, as a real screenshot would be."""
    ok, buf = cv2.imencode('.png', img)
    assert ok, "failed to encode test image"
    return buf.tobytes()


def _noise(h: int, w: int, seed: int) -> np.ndarray:
    """Deterministic textured BGR block - stands in for rendered page content."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


@pytest.fixture
def screenshot() -> np.ndarray:
    """A light 'page' with a distinct textured 'button' at a known position."""
    page = np.full((SCREEN_H, SCREEN_W, 3), 240, dtype=np.uint8)
    page[BUTTON_Y:BUTTON_Y + BUTTON_H, BUTTON_X:BUTTON_X + BUTTON_W] = _noise(
        BUTTON_H, BUTTON_W, seed=1
    )
    return page


@pytest.fixture
def screenshot_bytes(screenshot) -> bytes:
    return _encode(screenshot)


@pytest.fixture
def button_template(tmp_path, screenshot) -> str:
    """The button, cropped straight out of the screenshot - a guaranteed match."""
    crop = screenshot[BUTTON_Y:BUTTON_Y + BUTTON_H, BUTTON_X:BUTTON_X + BUTTON_W]
    path = tmp_path / "button.png"
    cv2.imwrite(str(path), crop)
    return str(path)


@pytest.fixture
def absent_template(tmp_path) -> str:
    """A textured element that appears nowhere in the screenshot."""
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), _noise(BUTTON_H, BUTTON_W, seed=999))
    return str(path)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_finds_template_at_its_center(screenshot_bytes, button_template):
    coords = find_image_in_screenshot(screenshot_bytes, button_template)

    assert coords == (BUTTON_X + BUTTON_W // 2, BUTTON_Y + BUTTON_H // 2)


def test_exact_crop_scores_near_one(screenshot_bytes, button_template):
    assert match_score(screenshot_bytes, button_template) == pytest.approx(1.0, abs=1e-3)


def test_check_image_exists_agrees_with_find(screenshot_bytes, button_template, absent_template):
    assert check_image_exists(screenshot_bytes, button_template) is True
    assert check_image_exists(screenshot_bytes, absent_template) is False


def test_colour_matching_also_locates_the_button(screenshot_bytes, button_template):
    coords = find_image_in_screenshot(screenshot_bytes, button_template, grayscale=False)

    assert coords == (BUTTON_X + BUTTON_W // 2, BUTTON_Y + BUTTON_H // 2)


# ---------------------------------------------------------------------------
# Regression: the TM_CCORR_NORMED fallback used to invent matches
# ---------------------------------------------------------------------------

def test_absent_template_is_not_found(screenshot_bytes, absent_template):
    """
    Regression: the old TM_CCORR_NORMED fallback accepted anything over 0.85,
    and CCORR scores 0.9+ on almost any pair of images. Absent elements came
    back with confident coordinates and callers clicked whatever sat there.
    """
    assert find_image_in_screenshot(screenshot_bytes, absent_template) is None


def test_absent_template_passes_the_old_ccorr_fallback(
    screenshot_bytes, absent_template
):
    """
    Pins down *why* the test above matters: confirm this fixture really does
    trip the old fallback, so the regression test cannot silently go stale.
    """
    img = cv2.cvtColor(
        cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR),
        cv2.COLOR_BGR2GRAY,
    )
    template = cv2.imread(absent_template, cv2.IMREAD_GRAYSCALE)

    ccoeff = cv2.minMaxLoc(cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED))[1]
    ccorr = cv2.minMaxLoc(cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED))[1]

    assert ccoeff < 0.7, "fixture no longer represents an absent element"
    assert ccorr >= 0.85, "fixture no longer trips the old CCORR fallback"


# ---------------------------------------------------------------------------
# Regression: zero-variance templates matched everywhere
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("colour", [(0, 0, 0), (255, 255, 255), (0, 0, 255)])
def test_solid_colour_template_is_rejected(tmp_path, screenshot_bytes, colour):
    """
    Regression: TM_CCOEFF_NORMED is 0/0 for a zero-variance template and OpenCV
    resolves that to 1.0 everywhere, so it matched at (0, 0) on any screenshot.
    """
    path = tmp_path / "solid.png"
    cv2.imwrite(str(path), np.full((50, 50, 3), colour, dtype=np.uint8))

    assert find_image_in_screenshot(screenshot_bytes, str(path)) is None
    assert match_score(screenshot_bytes, str(path)) is None


def test_solid_colour_template_still_degenerate_in_opencv(tmp_path, screenshot_bytes):
    """Confirms the guard is still load-bearing on the installed OpenCV."""
    img = cv2.cvtColor(
        cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR),
        cv2.COLOR_BGR2GRAY,
    )
    flat = np.full((50, 50), 76, dtype=np.uint8)

    raw = cv2.minMaxLoc(cv2.matchTemplate(img, flat, cv2.TM_CCOEFF_NORMED))[1]

    assert raw == pytest.approx(1.0), "OpenCV no longer degenerates; revisit the guard"


def test_near_flat_template_is_still_matchable(tmp_path):
    """The guard must reject only *truly* flat templates, not low-contrast ones."""
    rng = np.random.default_rng(42)
    # Mid grey with a +/-2 level dither: almost invisible, but genuinely textured.
    patch = (128 + rng.integers(0, 5, size=(40, 40, 3))).astype(np.uint8)
    assert patch.std() > 0, "fixture must not be flat"

    page = np.full((SCREEN_H, SCREEN_W, 3), 240, dtype=np.uint8)
    page[100:140, 100:140] = patch

    path = tmp_path / "low_contrast.png"
    cv2.imwrite(str(path), patch)

    assert find_image_in_screenshot(_encode(page), str(path)) == (120, 120)


# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------

def test_confidence_is_an_inclusive_lower_bound(screenshot_bytes, button_template):
    score = match_score(screenshot_bytes, button_template)

    assert find_image_in_screenshot(screenshot_bytes, button_template, confidence=score) is not None


def test_confidence_above_the_score_rejects_the_match(screenshot_bytes, absent_template):
    score = match_score(screenshot_bytes, absent_template)

    assert find_image_in_screenshot(
        screenshot_bytes, absent_template, confidence=score + 0.01
    ) is None
    assert find_image_in_screenshot(
        screenshot_bytes, absent_template, confidence=score - 0.01
    ) is not None


def test_zero_confidence_keeps_flat_template_rejected(tmp_path, screenshot_bytes):
    """A rejected template stays rejected however low the threshold goes."""
    path = tmp_path / "solid.png"
    cv2.imwrite(str(path), np.full((50, 50, 3), 200, dtype=np.uint8))

    assert find_image_in_screenshot(screenshot_bytes, str(path), confidence=0.0) is None


# ---------------------------------------------------------------------------
# Boundary conditions and malformed input
# ---------------------------------------------------------------------------

def test_template_exactly_the_size_of_the_screenshot(tmp_path, screenshot, screenshot_bytes):
    path = tmp_path / "whole_page.png"
    cv2.imwrite(str(path), screenshot)

    assert find_image_in_screenshot(screenshot_bytes, str(path)) == (
        SCREEN_W // 2,
        SCREEN_H // 2,
    )


@pytest.mark.parametrize(
    "shape",
    [
        (SCREEN_H + 1, SCREEN_W),      # one row too tall
        (SCREEN_H, SCREEN_W + 1),      # one column too wide
        (SCREEN_H * 2, SCREEN_W * 2),  # comfortably too large
    ],
)
def test_template_larger_than_screenshot_returns_none(tmp_path, screenshot_bytes, shape):
    path = tmp_path / "oversized.png"
    cv2.imwrite(str(path), _noise(shape[0], shape[1], seed=7))

    assert find_image_in_screenshot(screenshot_bytes, str(path)) is None


def test_single_pixel_template_is_rejected_as_flat(tmp_path, screenshot_bytes):
    path = tmp_path / "pixel.png"
    cv2.imwrite(str(path), np.full((1, 1, 3), 17, dtype=np.uint8))

    assert find_image_in_screenshot(screenshot_bytes, str(path)) is None


def test_missing_template_file_returns_none(screenshot_bytes, tmp_path):
    missing = str(tmp_path / "does_not_exist.png")

    assert find_image_in_screenshot(screenshot_bytes, missing) is None
    assert match_score(screenshot_bytes, missing) is None
    assert check_image_exists(screenshot_bytes, missing) is False


def test_unreadable_template_file_returns_none(tmp_path, screenshot_bytes):
    """A file that exists but is not a decodable image."""
    path = tmp_path / "not_an_image.png"
    path.write_bytes(b"this is not a PNG")

    assert find_image_in_screenshot(screenshot_bytes, str(path)) is None


@pytest.mark.parametrize("payload", [b"", b"garbage", b"\x89PNG\r\n\x1a\n truncated"])
def test_undecodable_screenshot_returns_none(payload, button_template):
    assert find_image_in_screenshot(payload, button_template) is None
    assert match_score(payload, button_template) is None


def test_best_match_reports_score_and_center(screenshot_bytes, button_template):
    match = _best_match(screenshot_bytes, button_template)

    assert match.score == pytest.approx(1.0, abs=1e-3)
    assert (match.x, match.y) == (BUTTON_X + BUTTON_W // 2, BUTTON_Y + BUTTON_H // 2)


def test_best_match_reports_screenshot_size(screenshot_bytes, button_template):
    """Adapters need this to scale HiDPI screenshot pixels into CSS pixels."""
    match = _best_match(screenshot_bytes, button_template)

    assert (match.screenshot_width, match.screenshot_height) == (SCREEN_W, SCREEN_H)


def test_locate_match_applies_the_threshold(screenshot_bytes, button_template, absent_template):
    assert locate_match(screenshot_bytes, button_template) is not None
    assert locate_match(screenshot_bytes, absent_template) is None
