"""
Unit tests for miss diagnosis.

When a template does not match, the advice printed has to depend on *why*. The
old messages listed every possible cause at once, which sent people recapturing
templates when the element was simply not on screen yet.
"""

import cv2
import numpy as np
import pytest

from pyxelator.utils import explain_miss


PAGE_W, PAGE_H = 600, 400


def _encode(img):
    ok, buf = cv2.imencode('.png', img)
    assert ok
    return buf.tobytes()


def _textured(h, w, seed):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


@pytest.fixture
def page():
    page = np.full((PAGE_H, PAGE_W, 3), 240, np.uint8)
    page[150:190, 200:320] = _textured(40, 120, seed=1)
    return page


@pytest.fixture
def screenshot(page):
    return _encode(page)


def _text(lines):
    return " ".join(lines).lower()


# ---------------------------------------------------------------------------
# The diagnosis must distinguish the causes
# ---------------------------------------------------------------------------

def test_near_miss_recommends_a_workable_confidence(tmp_path, page, screenshot):
    """A template that almost matches should get a concrete number to try."""
    faded = page[150:190, 200:320].astype(np.int16)
    faded = np.clip(faded * 0.93 + 8, 0, 255).astype(np.uint8)
    path = tmp_path / "faded.png"
    cv2.imwrite(str(path), faded)

    lines = explain_miss(screenshot, str(path), confidence=0.999)
    text = _text(lines)

    assert "confidence=" in text
    assert "close" in text


def test_absent_element_says_it_is_not_on_screen(tmp_path, screenshot):
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), _textured(40, 120, seed=999))

    text = _text(explain_miss(screenshot, str(path), confidence=0.7))

    assert "not on" in text and "screen" in text
    # Must NOT send the user off recapturing when that is not the problem.
    assert "recapture" not in text


def test_flat_template_is_named_as_the_cause(tmp_path, screenshot):
    path = tmp_path / "solid.png"
    cv2.imwrite(str(path), np.full((40, 40, 3), 90, np.uint8))

    text = _text(explain_miss(screenshot, str(path), confidence=0.7))

    assert "solid" in text and "colour" in text


def test_oversized_template_is_named_as_the_cause(tmp_path, screenshot):
    path = tmp_path / "huge.png"
    cv2.imwrite(str(path), _textured(PAGE_H * 2, PAGE_W * 2, seed=4))

    text = _text(explain_miss(screenshot, str(path), confidence=0.7))

    assert "larger than the screenshot" in text


def test_unreadable_file_is_named_as_the_cause(tmp_path, screenshot):
    path = tmp_path / "broken.png"
    path.write_bytes(b"not an image")

    text = _text(explain_miss(screenshot, str(path), confidence=0.7))

    assert "readable image" in text


def test_scale_mismatch_is_reported_with_the_factor(tmp_path, page, screenshot):
    """
    A template captured on a wider window than the page is now rendered at. The
    diagnosis should name the factor and the automatic range - otherwise the user
    has no way to know whether recapturing is even needed.
    """
    element = page[150:190, 200:320]
    bigger = cv2.resize(element, (round(element.shape[1] * 1.2), round(element.shape[0] * 1.2)),
                        interpolation=cv2.INTER_CUBIC)
    path = tmp_path / "bigger_element.png"
    cv2.imwrite(str(path), bigger)

    text = _text(explain_miss(screenshot, str(path), confidence=0.99))

    assert "x the template's size" in text
    assert "0.66x to 1.54x" in text


def test_scale_is_not_reported_for_a_hopeless_match(tmp_path, page, screenshot):
    """
    Regression: the winning scale of a near-zero match is noise. Reporting it
    told users to recapture a template whose size was never the problem.
    """
    element = page[150:190, 200:320]
    far_too_big = cv2.resize(element, (element.shape[1] * 3, element.shape[0] * 3),
                             interpolation=cv2.INTER_CUBIC)
    path = tmp_path / "way_off.png"
    cv2.imwrite(str(path), far_too_big)

    text = _text(explain_miss(screenshot, str(path), confidence=0.7))

    assert "template's size" not in text
    assert "recapture" not in text


def test_matching_template_does_not_claim_a_scale_problem(tmp_path, page, screenshot):
    """No spurious scale advice when the size was never the issue."""
    path = tmp_path / "exact.png"
    cv2.imwrite(str(path), page[150:190, 200:320])

    text = _text(explain_miss(screenshot, str(path), confidence=0.999))

    assert "template's size" not in text


# ---------------------------------------------------------------------------
# Shape of the output
# ---------------------------------------------------------------------------

def test_reports_the_actual_score(tmp_path, screenshot):
    """
    The score is the single most useful number and was never shown before -
    users were told to lower confidence with no idea what to lower it to.
    """
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), _textured(40, 120, seed=42))

    lines = explain_miss(screenshot, str(path), confidence=0.7)

    assert "scored" in lines[0]
    assert "0.70 threshold" in lines[0]


def test_returns_plain_lines_without_the_log_prefix(tmp_path, screenshot):
    """Adapters add '[Pyxelator] '; the helper must not double it up."""
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), _textured(40, 120, seed=7))

    for line in explain_miss(screenshot, str(path), confidence=0.7):
        assert not line.startswith("[Pyxelator")


def test_never_raises_on_a_broken_screenshot(tmp_path):
    path = tmp_path / "t.png"
    cv2.imwrite(str(path), _textured(20, 20, seed=1))

    lines = explain_miss(b"not a screenshot", str(path), confidence=0.7)

    assert lines and all(isinstance(line, str) for line in lines)
