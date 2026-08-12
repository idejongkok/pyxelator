"""
Unit tests for multi-scale template matching.

A template captured at one window size must still be found when the page is
rendered at another.

The fixture looks like a rendered UI rather than random noise, because tolerance
depends on spatial frequency: fine noise stops matching after ~2% of scale
change, UI chrome takes ~5-6%. Both on-ladder and off-ladder factors are tested,
since testing only the exact ladder values would hide the gaps between them.
"""

import cv2
import numpy as np
import pytest

from pyxelator.core import (
    DEFAULT_SCALES,
    _FAST_PATH_SCORE,
    find_image_in_screenshot,
    locate_match,
    match_score,
)


PAGE_W, PAGE_H = 1280, 800
BTN_X, BTN_Y, BTN_W, BTN_H = 880, 600, 170, 44

BLUE, BLUE_EDGE, WHITE = (223, 108, 45), (180, 86, 32), (255, 255, 255)


def _encode(img):
    ok, buf = cv2.imencode('.png', img)
    assert ok
    return buf.tobytes()


def _draw_button(page, x, y, label):
    cv2.rectangle(page, (x, y), (x + BTN_W, y + BTN_H), BLUE, -1)
    cv2.rectangle(page, (x, y), (x + BTN_W, y + BTN_H), BLUE_EDGE, 2)
    cv2.putText(page, label, (x + 18, y + 29), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)


def _ui_page():
    """A plausible app screen: header, sidebar, a table, and a primary button."""
    page = np.full((PAGE_H, PAGE_W, 3), 248, np.uint8)
    cv2.rectangle(page, (0, 0), (PAGE_W, 64), WHITE, -1)
    cv2.rectangle(page, (0, 64), (240, PAGE_H), (240, 242, 245), -1)
    for i in range(8):
        cv2.rectangle(page, (24, 100 + i * 46), (200, 118 + i * 46), (205, 208, 214), -1)
    for i in range(6):
        cv2.rectangle(page, (280, 140 + i * 64), (1240, 180 + i * 64), WHITE, -1)
        cv2.rectangle(page, (300, 152 + i * 64), (520, 168 + i * 64), (210, 213, 219), -1)
        cv2.rectangle(page, (560, 152 + i * 64), (700, 168 + i * 64), (224, 227, 232), -1)
    _draw_button(page, BTN_X, BTN_Y, "Save Suite")
    return page


@pytest.fixture
def page():
    return _ui_page()


@pytest.fixture
def template(tmp_path, page):
    """The button as captured at 100%."""
    path = tmp_path / "save_suite.png"
    cv2.imwrite(str(path), page[BTN_Y:BTN_Y + BTN_H, BTN_X:BTN_X + BTN_W])
    return str(path)


def _rendered_at(page, factor):
    """The page as it would be screenshotted at a different window size."""
    h, w = page.shape[:2]
    interp = cv2.INTER_AREA if factor < 1.0 else cv2.INTER_CUBIC
    return _encode(cv2.resize(page, (round(w * factor), round(h * factor)),
                              interpolation=interp))


def _expected_center(factor):
    return (round((BTN_X + BTN_W / 2) * factor), round((BTN_Y + BTN_H / 2) * factor))


def _assert_on_target(coords, factor, tolerance=6):
    """The match must be the button itself, not merely *a* match somewhere."""
    assert coords is not None, f"not found at {factor}x"
    exp_x, exp_y = _expected_center(factor)
    dev = max(abs(coords[0] - exp_x), abs(coords[1] - exp_y))
    assert dev <= tolerance, (
        f"at {factor}x matched ({coords[0]}, {coords[1]}) but the button centre "
        f"is ({exp_x}, {exp_y}) - off by {dev}px"
    )


# ---------------------------------------------------------------------------
# The core win: a template survives a window-size change
# ---------------------------------------------------------------------------

ON_LADDER = [0.68, 0.75, 0.83, 0.91, 1.1, 1.21, 1.33, 1.46, 0.5, 2.0]
OFF_LADDER = [0.7, 0.72, 0.78, 0.87, 0.95, 1.15, 1.28, 1.4, 1.52]

# Inside single-scale tolerance, so multi-scale is not what rescues these.
WITHIN_TOLERANCE = [0.98, 1.02]


@pytest.mark.parametrize("factor", ON_LADDER)
def test_found_when_resize_matches_a_ladder_value(page, template, factor):
    _assert_on_target(find_image_in_screenshot(_rendered_at(page, factor), template), factor)


@pytest.mark.parametrize("factor", OFF_LADDER)
def test_found_when_resize_falls_between_ladder_values(page, template, factor):
    """
    The ladder steps ~10%, so most real window sizes land between two rungs and
    rely on the nearest one still being close enough.
    """
    _assert_on_target(find_image_in_screenshot(_rendered_at(page, factor), template), factor)


@pytest.mark.parametrize("factor", ON_LADDER + OFF_LADDER)
def test_single_scale_matching_would_have_failed(page, template, factor):
    """Confirms every factor above genuinely defeats fixed-size matching."""
    assert find_image_in_screenshot(_rendered_at(page, factor), template, scales=(1.0,)) is None


@pytest.mark.parametrize("factor", WITHIN_TOLERANCE)
def test_tiny_resize_needs_no_help_from_the_ladder(page, template, factor):
    """
    A 2% change still matches unscaled. Marks where the ladder starts being
    load-bearing, and keeps the test above honest about what it proves.
    """
    coords = find_image_in_screenshot(_rendered_at(page, factor), template, scales=(1.0,))

    _assert_on_target(coords, factor, tolerance=8)


def test_unresized_page_matches_at_scale_one(page, template):
    match = locate_match(_encode(page), template)

    assert match.scale == 1.0
    assert match.score == pytest.approx(1.0, abs=1e-3)


def test_reported_scale_is_close_to_the_actual_resize(page, template):
    """Match.scale is the diagnostic that tells a user to recapture."""
    match = locate_match(_rendered_at(page, 0.8), template)

    assert match.scale == pytest.approx(0.8, abs=0.06)


# ---------------------------------------------------------------------------
# Regression: the fast path used to accept a marginal unscaled match
# ---------------------------------------------------------------------------

LOOKALIKE_CENTER = (300 + BTN_W // 2, 680 + BTN_H // 2)


def _page_with_lookalike(page, template, real_scale):
    """
    The real button rendered smaller, plus a same-size look-alike. Scale 1.0
    locks onto the look-alike with a middling score; stopping there returns the
    wrong element even though a later size matches the real one perfectly.
    """
    target = cv2.imread(template)
    page[BTN_Y:BTN_Y + BTN_H, BTN_X:BTN_X + BTN_W] = 248  # remove the original

    small = cv2.resize(target, (round(BTN_W * real_scale), round(BTN_H * real_scale)),
                       interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    page[520:520 + sh, 700:700 + sw] = small
    _draw_button(page, 300, 680, "Save Draft")

    return _encode(page), (700 + sw // 2, 520 + sh // 2)


@pytest.fixture
def page_with_lookalike(page, template):
    """Real button at an exact ladder value, so it scores ~1.0 when found."""
    return _page_with_lookalike(page, template, 0.83)


def test_lookalike_at_scale_one_does_not_win(page_with_lookalike, template):
    """Regression test - see _page_with_lookalike."""
    shot, real_center = page_with_lookalike

    match = locate_match(shot, template, confidence=0.7)

    assert match is not None
    assert (match.x, match.y) == pytest.approx(real_center, abs=6)
    assert (match.x, match.y) != pytest.approx(LOOKALIKE_CENTER, abs=20)


def test_lookalike_would_have_triggered_the_old_fast_path(
    page_with_lookalike, template
):
    """
    Pins the fixture down: the look-alike must score above a usable confidence
    but below _FAST_PATH_SCORE, or the test above proves nothing.
    """
    shot, _ = page_with_lookalike

    unscaled = match_score(shot, template, scales=(1.0,))

    assert 0.7 <= unscaled < _FAST_PATH_SCORE


@pytest.mark.xfail(
    reason="Known limitation: the element sits 3.6% off a rung so it peaks at "
           "0.771, under the 0.782 a same-size look-alike scores. Needs a finer "
           "ladder or scale-invariant features, not a threshold tweak.",
    strict=True,
)
def test_offrung_element_loses_to_an_onrung_lookalike(page, template):
    """Documents the failure mode rather than hiding it."""
    shot, real_center = _page_with_lookalike(page, template, 0.8)

    match = locate_match(shot, template, confidence=0.7)

    assert (match.x, match.y) == pytest.approx(real_center, abs=6)


def test_fast_path_floor_is_above_usable_confidence():
    """
    Short-circuiting at the caller's confidence is what caused the bug above.
    The floor must stay well clear of the thresholds users actually pass.
    """
    assert _FAST_PATH_SCORE >= 0.9


# ---------------------------------------------------------------------------
# Multi-scale must not manufacture matches
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("factor", [0.75, 0.85, 1.0, 1.25])
def test_absent_element_stays_absent_at_every_scale(page, tmp_path, factor):
    """
    Ten scales means ten chances to exceed the threshold. An element that is
    not on the page must still not be found.
    """
    absent = np.full((BTN_H, BTN_W, 3), 248, np.uint8)
    _draw_button(absent, 0, 0, "Delete All")
    # Give it a distinctly different colour so it is not the same widget.
    absent[:, :, 0], absent[:, :, 2] = absent[:, :, 2].copy(), absent[:, :, 0].copy()
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), absent)

    assert find_image_in_screenshot(_rendered_at(page, factor), str(path)) is None


def test_flat_template_rejected_regardless_of_scale(page, tmp_path):
    """No resize can rescue a zero-variance template."""
    path = tmp_path / "solid.png"
    cv2.imwrite(str(path), np.full((60, 60, 3), 111, dtype=np.uint8))

    assert find_image_in_screenshot(_encode(page), str(path)) is None
    assert match_score(_encode(page), str(path)) is None


def test_tiny_template_is_not_shrunk_into_noise(page, tmp_path):
    """
    A 12px template at scale 0.5 would be 6px - too little structure to identify
    anything. Such scales must be skipped rather than matched blindly.
    """
    rng = np.random.default_rng(5)
    path = tmp_path / "tiny.png"
    cv2.imwrite(str(path), rng.integers(0, 256, size=(12, 12, 3), dtype=np.uint8))

    match = locate_match(_encode(page), str(path), confidence=0.0)

    assert match is None or round(12 * match.scale) >= 8


# ---------------------------------------------------------------------------
# The scale ladder itself
# ---------------------------------------------------------------------------

def test_scale_one_is_tried_first():
    """The fast path depends on it, and it is by far the common case."""
    assert DEFAULT_SCALES[0] == 1.0


def test_exact_device_pixel_ratio_rungs_are_present():
    """A DPR change is an exact doubling or halving, not an arbitrary resize."""
    assert 0.5 in DEFAULT_SCALES and 2.0 in DEFAULT_SCALES


def test_dense_band_has_no_gaps():
    """
    Rungs within ~11% of each other, so nothing sits more than ~5% away. An
    earlier ladder used round numbers (0.75, 1.25, 1.5), left 34% gaps, and
    matched nothing at 0.58x, 1.35x or 1.7x.
    """
    dense = sorted(s for s in DEFAULT_SCALES if 0.6 <= s <= 1.5)

    assert len(dense) >= 8, "too few rungs to cover the band"
    for lower, upper in zip(dense, dense[1:]):
        assert upper / lower <= 1.11, f"gap between {lower} and {upper} is too wide"


@pytest.mark.parametrize("factor", [0.66, 1.0, 1.54])
def test_documented_coverage_bounds_hold(page, template, factor):
    """The range core.py claims to cover, pinned so the claim cannot rot."""
    _assert_on_target(find_image_in_screenshot(_rendered_at(page, factor), template), factor)


def test_below_the_documented_floor_is_a_clean_miss(page, template):
    """
    core.py states coverage stops below 0.66x. Outside the covered range the
    answer must be None - reporting wrong coordinates would be far worse than
    admitting the template was not found.
    """
    assert find_image_in_screenshot(_rendered_at(page, 0.6), template) is None


def test_explicit_scales_are_respected(page, template):
    """A caller restricting the search must not silently get the defaults."""
    shot = _rendered_at(page, 0.8)

    assert find_image_in_screenshot(shot, template, scales=(1.0, 1.1)) is None
    assert find_image_in_screenshot(shot, template, scales=(1.0, 0.8)) is not None
