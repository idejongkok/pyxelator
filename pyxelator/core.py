"""
Core image matching functionality.

This module contains the core computer vision logic for template matching
that is shared across all adapters (Selenium, Playwright, Appium, etc).
"""

import cv2
import numpy as np
from typing import List, NamedTuple, Tuple, Optional

from .results import MatchCandidate, MatchResult, Rectangle


class Match(NamedTuple):
    """
    A located template, in screenshot pixel coordinates.

    Screenshot pixels are not CSS pixels on a HiDPI display, where the
    screenshot is typically 2x the viewport. Pass this through
    utils.to_css_pixels before feeding coordinates back to the driver.

    scale is the template size the match was found at. Anything other than 1.0
    means the template was captured at a different window size.
    """
    x: int
    y: int
    score: float
    screenshot_width: int
    screenshot_height: int
    scale: float = 1.0


# A solid-colour template makes TM_CCOEFF_NORMED evaluate 0/0, which OpenCV
# resolves to 1.0 at every offset - so it would "match" anywhere. Reject it.
_MIN_TEMPLATE_STD = 1e-6

# Template sizes to try, ordered outward from 1.0. Geometric with ratio ~1.10,
# which keeps every size in 0.66x-1.54x within 5% of a rung - matching tolerates
# about 5-6% of scale error on UI content and nothing like 10%, so wider steps
# leave sizes that match nothing. 0.5 and 2.0 cover a device pixel ratio change,
# which is an exact doubling and needs no neighbours.
# Set to (1.0,) to disable multi-scale matching.
DEFAULT_SCALES = (
    1.0,
    0.91, 1.1,
    0.83, 1.21,
    0.75, 1.33,
    0.68, 1.46,
    0.5, 2.0,
)

# Below this many pixels a side, a scaled template has too little detail left
_MIN_SCALED_SIDE = 8

# Score at which an unscaled match is good enough to skip the other sizes. Well
# above any usable confidence on purpose: a marginal score at 1.0 is exactly
# when another size holds the real element. With a page rendered at 0.9x, scale
# 1.0 scored 0.738 on the wrong element and scale 0.9 scored 0.963 on the right.
_FAST_PATH_SCORE = 0.9


def _resize_template(template: np.ndarray, scale: float) -> Optional[np.ndarray]:
    """Resize a template, or None if the result would be too small to trust."""
    if scale == 1.0:
        return template

    h, w = template.shape[:2]
    new_h, new_w = round(h * scale), round(w * scale)
    if new_h < _MIN_SCALED_SIDE or new_w < _MIN_SCALED_SIDE:
        return None

    # INTER_AREA is the right choice for shrinking, INTER_CUBIC for enlarging.
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(template, (new_w, new_h), interpolation=interpolation)


def _match_at_scale(
    img: np.ndarray,
    template: np.ndarray,
    scale: float
) -> Optional[Tuple[float, int, int]]:
    """
    Match a single resized template.

    Returns:
        (score, center_x, center_y) in screenshot pixels, or None if this scale
        is not usable against this screenshot.
    """
    scaled = _resize_template(template, scale)
    if scaled is None:
        return None

    h, w = scaled.shape[:2]
    img_h, img_w = img.shape[:2]
    if h > img_h or w > img_w:
        return None

    # Shrinking can flatten a finely textured template into a uniform block
    if float(scaled.std()) < _MIN_TEMPLATE_STD:
        return None

    result = cv2.matchTemplate(img, scaled, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    return float(max_val), max_loc[0] + w // 2, max_loc[1] + h // 2


def _best_match(
    screenshot_bytes: bytes,
    template_path: str,
    grayscale: bool = True,
    scales: Optional[Tuple[float, ...]] = None,
    stop_at: Optional[float] = None
) -> Optional[Match]:
    """
    Locate the best position of the template within the screenshot.

    The template is tried at several sizes, so a template captured at one
    window size still matches at another.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        grayscale: Match on luminance only (default: True). Set False to match
            on colour, which is slower but distinguishes elements that differ
            only by hue.
        scales: Template resize factors to try (default: DEFAULT_SCALES)
        stop_at: Return as soon as an unscaled match reaches this score,
            without trying the other scales. None searches every scale and
            returns the true best.

    Returns:
        The highest-scoring Match found, regardless of any threshold, or None
        if no scale could be matched at all (unreadable image, flat template,
        template larger than the screenshot at every scale).
    """
    nparr = np.frombuffer(screenshot_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    template = cv2.imread(
        template_path,
        cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    )
    if template is None:
        return None

    if grayscale:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # No amount of resizing rescues a flat template
    if float(template.std()) < _MIN_TEMPLATE_STD:
        return None

    img_h, img_w = img.shape[:2]
    if scales is None:
        scales = DEFAULT_SCALES

    best = None
    for scale in scales:
        result = _match_at_scale(img, template, scale)
        if result is None:
            continue

        score, x, y = result
        if best is None or score > best.score:
            best = Match(
                x=x,
                y=y,
                score=score,
                screenshot_width=img_w,
                screenshot_height=img_h,
                scale=scale,
            )

        # Near-perfect at the captured size, nothing left to improve on
        if (
            scale == 1.0
            and stop_at is not None
            and score >= max(stop_at, _FAST_PATH_SCORE)
        ):
            break

    return best


def find_image_in_screenshot(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7,
    grayscale: bool = True,
    scales: Optional[Tuple[float, ...]] = None
) -> Optional[Tuple[int, int]]:
    """
    Locate element by image template matching using OpenCV.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        confidence: Match confidence threshold 0.0-1.0 (default: 0.7)
        grayscale: Use grayscale matching (default: True)
        scales: Template resize factors to try (default: DEFAULT_SCALES).
            Pass (1.0,) to match only at the captured size.

    Returns:
        (x, y) center coordinates of matched element, or None if not found

    Algorithm:
        1. Decode screenshot from bytes to OpenCV image
        2. Load the template and reject it if it carries no pixel variance
        3. Use cv2.matchTemplate with TM_CCOEFF_NORMED, at each scale in turn
        4. Return center coordinates if the confidence threshold is met

    Note:
        Only TM_CCOEFF_NORMED is used. Do not add TM_CCORR_NORMED as a
        fallback: it does not subtract the mean, so it scores 0.93-0.99 on
        almost any pair of images and reports confident matches for elements
        that are not on screen.
    """
    match = locate_match(screenshot_bytes, template_path, confidence, grayscale, scales)
    return None if match is None else (match.x, match.y)


def _same_spatial_candidate(first: MatchCandidate, second: MatchCandidate) -> bool:
    """Return whether candidates at different scales identify the same target."""
    first_x, first_y = first.coordinates
    second_x, second_y = second.coordinates
    return (
        abs(first_x - second_x)
        < max(1, min(first.location.width, second.location.width) // 2)
        and abs(first_y - second_y)
        < max(1, min(first.location.height, second.location.height) // 2)
    )


def _rank_match_candidates(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float,
    grayscale: bool,
    scales: Optional[Tuple[float, ...]],
    max_candidates: int = 8,
) -> Tuple[MatchCandidate, ...]:
    """Rank spatially distinct candidates across all requested scales.

    The strongest location at every usable scale is retained even below the
    threshold so a miss still has diagnostic evidence. Additional locations
    are collected only while they meet ``confidence``. Non-maximum suppression
    prevents nearby response-map peaks and scale variants of the same element
    from being mistaken for separate candidates.
    """
    img = cv2.imdecode(
        np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR
    )
    if img is None:
        return ()

    template = cv2.imread(
        template_path,
        cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR,
    )
    if template is None or float(template.std()) < _MIN_TEMPLATE_STD:
        return ()

    if grayscale:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    img_h, img_w = img.shape[:2]
    attempted_scales = DEFAULT_SCALES if scales is None else scales
    raw_candidates: List[MatchCandidate] = []

    for scale in attempted_scales:
        scaled = _resize_template(template, scale)
        if scaled is None or float(scaled.std()) < _MIN_TEMPLATE_STD:
            continue

        height, width = scaled.shape[:2]
        if height > img_h or width > img_w:
            continue

        scores = cv2.matchTemplate(img, scaled, cv2.TM_CCOEFF_NORMED)
        # Work on a copy because suppression mutates the response map.
        remaining = scores.copy()
        for rank_at_scale in range(max_candidates):
            _, score, _, top_left = cv2.minMaxLoc(remaining)
            if rank_at_scale > 0 and score < confidence:
                break

            location = Rectangle(
                x=top_left[0],
                y=top_left[1],
                width=width,
                height=height,
            )
            raw_candidates.append(
                MatchCandidate(score=float(score), location=location, scale=scale)
            )

            # A shifted peak from the same visual element is not a runner-up.
            # Suppress top-left positions up to one template size away; two
            # adjacent, non-overlapping instances remain independently ranked.
            left = max(0, top_left[0] - width + 1)
            right = min(remaining.shape[1], top_left[0] + width)
            top = max(0, top_left[1] - height + 1)
            bottom = min(remaining.shape[0], top_left[1] + height)
            remaining[top:bottom, left:right] = -2.0

    ranked: List[MatchCandidate] = []
    for candidate in sorted(raw_candidates, key=lambda item: item.score, reverse=True):
        if any(_same_spatial_candidate(candidate, kept) for kept in ranked):
            continue
        ranked.append(candidate)
        if len(ranked) >= max_candidates:
            break

    return tuple(ranked)


def _unusable_match_reason(
    screenshot_bytes: bytes,
    template_path: str,
    grayscale: bool,
    scales: Optional[Tuple[float, ...]],
) -> str:
    """Classify why no candidate could be scored."""
    try:
        img = cv2.imdecode(
            np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR
        )
    except Exception:
        return "invalid_screenshot"
    if img is None:
        return "invalid_screenshot"

    template = cv2.imread(
        template_path,
        cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR,
    )
    if template is None:
        return "invalid_template"
    if float(template.std()) < _MIN_TEMPLATE_STD:
        return "flat_template"

    img_h, img_w = img.shape[:2]
    attempted_scales = DEFAULT_SCALES if scales is None else scales
    any_size_fits = False
    for scale in attempted_scales:
        scaled = _resize_template(template, scale)
        if scaled is None:
            continue
        height, width = scaled.shape[:2]
        if height <= img_h and width <= img_w:
            any_size_fits = True
            if float(scaled.std()) >= _MIN_TEMPLATE_STD:
                # Reaching this branch means OpenCV could have scored a
                # candidate; reserve a generic reason for unexpected cases.
                return "match_error"

    return "no_usable_scale" if any_size_fits else "template_too_large"


def match_result(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7,
    grayscale: bool = True,
    scales: Optional[Tuple[float, ...]] = None,
    ambiguity_margin: float = 0.02,
) -> MatchResult:
    """Match a template and return ranked evidence whether or not it is safe.

    Unlike :func:`locate_match`, a below-threshold result retains the best
    candidate's score, bounds, and scale. A match is unsafe when a second,
    spatially distinct candidate also meets ``confidence`` and its score is
    within ``ambiguity_margin`` of the winner. Invalid inputs return a stable
    machine-readable ``reason`` rather than raising. Existing legacy helpers keep
    both their return values and their original matching path.
    """
    try:
        candidates = _rank_match_candidates(
            screenshot_bytes, template_path, confidence, grayscale, scales
        )
        if not candidates:
            reason = _unusable_match_reason(
                screenshot_bytes, template_path, grayscale, scales
            )
            return MatchResult(
                ok=False,
                found=False,
                score=None,
                threshold=confidence,
                location=None,
                scale=None,
                reason=reason,
            )

        winner = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        found = winner.score >= confidence
        score_margin = (
            winner.score - runner_up.score if runner_up is not None else None
        )
        ambiguous = bool(
            found
            and runner_up is not None
            and runner_up.score >= confidence
            and score_margin is not None
            and score_margin <= ambiguity_margin
        )

        return MatchResult(
            ok=found and not ambiguous,
            found=found,
            score=winner.score,
            threshold=confidence,
            location=winner.location,
            scale=winner.scale,
            ambiguous=ambiguous,
            reason=(
                "ambiguous_match"
                if ambiguous
                else None if found else "below_threshold"
            ),
            candidates=candidates,
            score_margin=score_margin,
        )
    except Exception:
        try:
            reason = _unusable_match_reason(
                screenshot_bytes, template_path, grayscale, scales
            )
        except Exception:
            reason = "match_error"
        return MatchResult(
            ok=False,
            found=False,
            score=None,
            threshold=confidence,
            location=None,
            scale=None,
            reason=reason,
        )


def locate_match(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7,
    grayscale: bool = True,
    scales: Optional[Tuple[float, ...]] = None
) -> Optional[Match]:
    """
    Locate a template and report the full Match, including screenshot size.

    Same matching as find_image_in_screenshot, but the extra fields let callers
    convert screenshot pixels to CSS pixels, report the score on failure, and
    see which scale the template matched at.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        confidence: Match confidence threshold 0.0-1.0 (default: 0.7)
        grayscale: Use grayscale matching (default: True)
        scales: Template resize factors to try (default: DEFAULT_SCALES)

    Returns:
        Match if the score meets the threshold, None otherwise
    """
    try:
        match = _best_match(
            screenshot_bytes, template_path, grayscale, scales, stop_at=confidence
        )
    except Exception:
        return None

    if match is None or match.score < confidence:
        return None

    return match


def match_score(
    screenshot_bytes: bytes,
    template_path: str,
    grayscale: bool = True,
    scales: Optional[Tuple[float, ...]] = None
) -> Optional[float]:
    """
    Return the best correlation score for a template, ignoring any threshold.

    Useful for choosing a confidence value: if find() reports nothing, this
    shows how close the template actually came. Every scale is searched, so
    this is slower than a successful find().

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        grayscale: Use grayscale matching (default: True)
        scales: Template resize factors to try (default: DEFAULT_SCALES)

    Returns:
        Score in the range -1.0 to 1.0, or None if the match could not be
        computed. Scores at or above the `confidence` passed to find() are
        treated as a match.

    Example:
        from pyxelator import match_score

        print(match_score(driver.get_screenshot_as_png(), 'button.png'))
        # 0.62  ->  the element is probably there; try confidence=0.6
        # 0.13  ->  the element is not on screen

        # To see which size it matched at, ask for the whole Match:
        from pyxelator.core import locate_match
        m = locate_match(shot, 'button.png', confidence=0.0)
        print(m.score, m.scale)   # 0.94 0.8 -> captured on a wider window
    """
    try:
        match = _best_match(screenshot_bytes, template_path, grayscale, scales)
    except Exception:
        return None

    return None if match is None else match.score


def image_sizes(
    screenshot_bytes: bytes,
    template_path: str
) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Report the size of a screenshot and a template, for diagnostics.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file

    Returns:
        ((screenshot_w, screenshot_h), (template_w, template_h)), or None if
        either image could not be read.
    """
    try:
        img = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_COLOR)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if img is None or template is None:
            return None

        img_h, img_w = img.shape[:2]
        tpl_h, tpl_w = template.shape[:2]
        return (img_w, img_h), (tpl_w, tpl_h)
    except Exception:
        return None


def check_image_exists(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7
) -> bool:
    """
    Check if image template exists in screenshot.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        confidence: Match confidence threshold 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise
    """
    return find_image_in_screenshot(screenshot_bytes, template_path, confidence) is not None
