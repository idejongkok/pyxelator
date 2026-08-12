"""
Utility functions for Pyxelator.

Includes driver type detection and helper functions.
"""

from typing import List, Tuple

from .core import Match, image_sizes, locate_match


# A screenshot is normally 1x-3x the coordinate space. Outside this range we
# have measured something unexpected, so leave the coordinates alone.
_MIN_SCALE = 0.1
_MAX_SCALE = 10.0


def to_css_pixels(match: Match, viewport_width: float) -> Tuple[int, int]:
    """
    Convert screenshot-pixel coordinates into the driver's coordinate space.

    HiDPI browser screenshots are 2x the CSS viewport and iOS screenshots are
    2-3x the tap space, so raw coordinates miss the target by that factor.

    The ratio is measured from the images rather than read from
    window.devicePixelRatio, so a driver whose screenshots are already in the
    coordinate space scales by 1.0 and is left untouched.

    Args:
        match: Match returned by core.locate_match
        viewport_width: Width of the driver's coordinate space. CSS pixels for
            browsers (window.innerWidth), points for Appium (window size)

    Returns:
        (x, y) in the driver's coordinate space, or the unmodified screenshot
        coordinates if the ratio cannot be trusted
    """
    if not viewport_width or match.screenshot_width <= 0:
        return match.x, match.y

    scale = viewport_width / match.screenshot_width
    if not (_MIN_SCALE <= scale <= _MAX_SCALE):
        return match.x, match.y

    return round(match.x * scale), round(match.y * scale)


def explain_miss(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float
) -> List[str]:
    """
    Work out why a template did not match.

    Scoring the template first separates "close, lower the threshold" from
    "not on screen at all", which need opposite fixes.

    Args:
        screenshot_bytes: Screenshot the match was attempted against
        template_path: Path to the template that missed
        confidence: Threshold that was not met

    Returns:
        Lines to print, already ordered most useful first
    """
    match = locate_match(screenshot_bytes, template_path, confidence=-1.0)

    if match is None:
        return [
            "The template could not be matched at all. Usually one of:",
            "  - it is a solid block of one colour, with no detail to match on",
            "  - it is larger than the screenshot at every size tried",
            "  - the file is not a readable image",
        ]

    # A template bigger than the screen only matches once shrunk, and badly
    sizes = image_sizes(screenshot_bytes, template_path)
    if sizes is not None:
        (shot_w, shot_h), (tpl_w, tpl_h) = sizes
        if tpl_w > shot_w or tpl_h > shot_h:
            return [
                f"The template ({tpl_w}x{tpl_h}) is larger than the screenshot "
                f"({shot_w}x{shot_h}).",
                "It looks like a screenshot of the whole page rather than of one",
                "element. Crop it down to just the button or field.",
            ]

    score = match.score
    lines = [f"Best match scored {score:.2f}, below the {confidence:.2f} threshold."]

    if score >= confidence - 0.15:
        lines += [
            "That is close. The element is probably there but rendered slightly",
            f"differently. Try confidence={max(score - 0.02, 0.0):.2f}.",
        ]
    elif score >= 0.4:
        lines += [
            "That is a weak, partial match. Likely causes:",
            "  - the template includes surrounding layout, not just the element",
            "  - the element is styled differently now (hover, disabled, theme)",
        ]
    else:
        lines += [
            "That is low enough that the element is almost certainly not on",
            "screen. Check it has finished rendering, and that nothing is",
            "covering it, before touching the template.",
        ]

    # The winning scale of a near-zero match is noise, not a size problem
    if match.scale != 1.0 and score >= 0.4:
        lines += [
            f"The closest match was at {match.scale:g}x the template's size, so it",
            "was captured at a different window size. Sizes from 0.66x to 1.54x",
            "are handled automatically; further out than that, recapture it.",
        ]

    return lines


def detect_driver_type(driver) -> str:
    """
    Auto-detect the type of automation driver.

    Args:
        driver: Any automation driver (Selenium, Playwright, Appium, etc.)

    Returns:
        One of: 'selenium', 'playwright', 'appium', or 'unknown'

    Detection logic:
        - Checks module name for known frameworks
        - Checks class name for Page (Playwright)
        - Checks for appium-specific attributes
    """
    # Get module and class name
    module = driver.__class__.__module__.lower()
    class_name = driver.__class__.__name__

    # Check for Playwright
    if 'playwright' in module or class_name == 'Page':
        return 'playwright'

    # Check for Appium
    if 'appium' in module:
        return 'appium'

    # Check for Selenium (default fallback)
    if 'selenium' in module:
        return 'selenium'

    # Check for WebDriver attributes (Selenium-like)
    if hasattr(driver, 'get_screenshot_as_png'):
        return 'selenium'

    # Check for Playwright attributes
    if hasattr(driver, 'screenshot') and hasattr(driver, 'evaluate'):
        return 'playwright'

    # Fallback to selenium (most common)
    return 'selenium'
