"""
Unit tests for coordinate-space conversion.

A screenshot is not always in the same coordinate space as the driver: HiDPI
browsers screenshot at 2x the CSS viewport, and iOS screenshots are 2-3x the
tap coordinate space. These tests pin down that conversion.
"""

import pytest

from pyxelator.core import Match
from pyxelator.utils import detect_driver_type, to_css_pixels


def _match(x, y, screenshot_width=1000):
    return Match(x=x, y=y, score=1.0, screenshot_width=screenshot_width,
                 screenshot_height=int(screenshot_width * 0.6))


# ---------------------------------------------------------------------------
# to_css_pixels
# ---------------------------------------------------------------------------

def test_standard_dpi_leaves_coordinates_untouched():
    assert to_css_pixels(_match(390, 242, screenshot_width=1000), 1000) == (390, 242)


def test_hidpi_screenshot_is_halved():
    """Regression: a 2x screenshot used to be fed straight to elementFromPoint."""
    assert to_css_pixels(_match(780, 484, screenshot_width=2000), 1000) == (390, 242)


@pytest.mark.parametrize("ratio", [1, 2, 3])
def test_common_device_pixel_ratios(ratio):
    """1x desktop, 2x retina, 3x phone - all must land on the same CSS point."""
    assert to_css_pixels(_match(300 * ratio, 200 * ratio, 1000 * ratio), 1000) == (300, 200)


def test_fractional_scaling_rounds_to_nearest():
    # 1.5x scaling: a 1500px screenshot of a 1000px viewport.
    assert to_css_pixels(_match(150, 300, screenshot_width=1500), 1000) == (100, 200)


def test_origin_is_invariant_under_scaling():
    assert to_css_pixels(_match(0, 0, screenshot_width=2000), 1000) == (0, 0)


# ---------------------------------------------------------------------------
# Defensive fallbacks - never corrupt coordinates on bad input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("viewport_width", [None, 0])
def test_unknown_viewport_falls_back_to_raw_coordinates(viewport_width):
    """If the JS probe failed we must not guess - pass the raw values through."""
    assert to_css_pixels(_match(780, 484, screenshot_width=2000), viewport_width) == (780, 484)


def test_zero_width_screenshot_falls_back_to_raw():
    assert to_css_pixels(_match(780, 484, screenshot_width=0), 1000) == (780, 484)


@pytest.mark.parametrize(
    "screenshot_width, viewport_width",
    [
        (1000, 100000),  # scale 100 - implausible
        (100000, 1000),  # scale 0.01 - implausible
    ],
)
def test_implausible_scale_is_ignored(screenshot_width, viewport_width):
    """
    A ratio far outside 0.1-10x means we measured something we do not
    understand. Leaving the coordinates alone is safer than scaling by it.
    """
    match = _match(780, 484, screenshot_width=screenshot_width)

    assert to_css_pixels(match, viewport_width) == (780, 484)


def test_returns_plain_ints_not_floats():
    """Drivers reject float coordinates in some Actions APIs."""
    x, y = to_css_pixels(_match(781, 485, screenshot_width=2000), 1000)

    assert isinstance(x, int) and isinstance(y, int)


# ---------------------------------------------------------------------------
# detect_driver_type
# ---------------------------------------------------------------------------

class _Fake:
    """Stands in for a driver, letting us control __module__ and __name__."""


def _driver(module, name, **attrs):
    cls = type(name, (_Fake,), {})
    cls.__module__ = module
    obj = cls()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


@pytest.mark.parametrize(
    "module, name, expected",
    [
        ("selenium.webdriver.chrome.webdriver", "WebDriver", "selenium"),
        ("playwright.sync_api._generated", "Page", "playwright"),
        ("playwright._impl._page", "Page", "playwright"),
        ("appium.webdriver.webdriver", "WebDriver", "appium"),
    ],
)
def test_detects_driver_by_module(module, name, expected):
    assert detect_driver_type(_driver(module, name)) == expected


def test_detects_playwright_page_by_class_name_alone():
    assert detect_driver_type(_driver("some.wrapper", "Page")) == "playwright"


def test_falls_back_to_selenium_for_unknown_drivers():
    assert detect_driver_type(_driver("mystery.lib", "Thing")) == "selenium"
