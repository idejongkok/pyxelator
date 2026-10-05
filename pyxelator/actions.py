"""Safe, structured actions built on the ambiguity-aware matcher."""

from typing import Optional, Tuple

import cv2
import numpy as np

from . import adapters
from .core import match_result
from .results import ActionResult, MatchResult, VerificationResult
from .utils import detect_driver_type

__all__ = ["click_result", "fill_result"]


def _driver_tools(driver):
    """Return screenshot, viewport, click, and fill primitives for a driver."""
    driver_type = detect_driver_type(driver)
    if driver_type == "playwright":
        return (
            adapters.playwright._get_screenshot,
            adapters.playwright._viewport_width,
            adapters.playwright._click_at,
            adapters.playwright._fill_at,
        )
    if driver_type == "appium":
        return (
            adapters.appium._get_screenshot,
            adapters.appium._viewport_width,
            adapters.appium._tap,
            adapters.appium._fill_at,
        )
    return (
        adapters.selenium._get_screenshot,
        adapters.selenium._viewport_width,
        adapters.selenium._click_at,
        adapters.selenium._fill_at,
    )


def _action_coordinates(
    screenshot: bytes,
    match: MatchResult,
    viewport_width: Optional[float],
) -> Optional[Tuple[int, int]]:
    """Convert a structured match from screenshot pixels to driver pixels."""
    coordinates = match.coordinates
    if coordinates is None:
        return None

    image = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
    if image is None or not viewport_width or image.shape[1] <= 0:
        return coordinates

    scale = viewport_width / image.shape[1]
    if not 0.1 <= scale <= 10.0:
        return coordinates
    return round(coordinates[0] * scale), round(coordinates[1] * scale)


def _verification_result(
    screenshot: bytes,
    image: str,
    confidence: float,
    ambiguity_margin: float,
    expected_visible: bool,
) -> VerificationResult:
    evidence = match_result(
        screenshot,
        image,
        confidence=confidence,
        ambiguity_margin=ambiguity_margin,
    )
    if expected_visible:
        ok = evidence.ok
        reason = None if ok else evidence.reason or "verification_failed"
        observed_visible = evidence.found
    else:
        observed_visible = evidence.found
        # Disappearance is proven only when matching was actually evaluated
        # and its best candidate scored below the threshold. Invalid images,
        # flat templates, unusable scales, and matcher errors are unknowns,
        # never evidence that the target is absent.
        evaluated_absence = bool(
            not evidence.found
            and not evidence.ambiguous
            and evidence.reason == "below_threshold"
            and evidence.score is not None
            and evidence.location is not None
        )
        ok = evaluated_absence
        if ok:
            reason = None
        elif evidence.ambiguous:
            reason = "ambiguous_match"
        elif evidence.found:
            reason = "unexpected_match"
        else:
            reason = evidence.reason or "verification_failed"
    return VerificationResult(
        ok=ok,
        expected_visible=expected_visible,
        observed_visible=observed_visible,
        match=evidence,
        reason=reason,
    )


def click_result(
    driver,
    image: str,
    confidence: float = 0.7,
    *,
    ambiguity_margin: float = 0.02,
    verify_image: Optional[str] = None,
    verification_confidence: Optional[float] = None,
    verification_expected_visible: bool = True,
    debug: bool = False,
) -> ActionResult:
    """Safely click one unambiguous visual target and return action evidence.

    The driver is never touched when the target is below ``confidence`` or a
    similarly scored, spatially distinct candidate makes it ambiguous. The
    optional ``verify_image`` is matched against a fresh screenshot after the
    click; set ``verification_expected_visible=False`` to verify disappearance.
    """
    screenshot_fn, viewport_fn, click_fn, _ = _driver_tools(driver)
    try:
        screenshot = screenshot_fn(driver)
    except Exception:
        return ActionResult(ok=False, action="click", reason="screenshot_failed")

    evidence = match_result(
        screenshot,
        image,
        confidence=confidence,
        ambiguity_margin=ambiguity_margin,
    )
    if not evidence.ok:
        return ActionResult(
            ok=False,
            action="click",
            match=evidence,
            reason=evidence.reason or "unsafe_match",
        )

    try:
        coordinates = _action_coordinates(screenshot, evidence, viewport_fn(driver))
        acted = coordinates is not None and click_fn(
            driver, coordinates[0], coordinates[1], debug
        )
    except Exception:
        acted = False

    if not acted:
        return ActionResult(
            ok=False,
            action="click",
            match=evidence,
            reason="click_failed",
        )

    verification = None
    if verify_image is not None:
        try:
            after = screenshot_fn(driver)
        except Exception:
            return ActionResult(
                ok=False,
                action="click",
                match=evidence,
                reason="verification_screenshot_failed",
            )
        verification = _verification_result(
            after,
            verify_image,
            confidence if verification_confidence is None else verification_confidence,
            ambiguity_margin,
            verification_expected_visible,
        )
        if not verification.ok:
            return ActionResult(
                ok=False,
                action="click",
                match=evidence,
                verification=verification,
                reason=verification.reason,
            )

    return ActionResult(
        ok=True,
        action="click",
        match=evidence,
        verification=verification,
    )


def fill_result(
    driver,
    image: str,
    text: str,
    confidence: float = 0.7,
    *,
    ambiguity_margin: float = 0.02,
    verify_image: Optional[str] = None,
    verification_confidence: Optional[float] = None,
    verification_expected_visible: bool = True,
    debug: bool = False,
) -> ActionResult:
    """Safely fill one unambiguous visual target and return action evidence.

    Matching and coordinate conversion happen once. The validated coordinates
    are passed directly to a framework-specific fill primitive, so this never
    calls the legacy fill path or performs a second, potentially different
    match. Optional verification uses a fresh screenshot after the write.
    """
    screenshot_fn, viewport_fn, _, fill_fn = _driver_tools(driver)
    try:
        screenshot = screenshot_fn(driver)
    except Exception:
        return ActionResult(ok=False, action="fill", reason="screenshot_failed")

    evidence = match_result(
        screenshot,
        image,
        confidence=confidence,
        ambiguity_margin=ambiguity_margin,
    )
    if not evidence.ok:
        return ActionResult(
            ok=False,
            action="fill",
            match=evidence,
            reason=evidence.reason or "unsafe_match",
        )

    try:
        coordinates = _action_coordinates(screenshot, evidence, viewport_fn(driver))
        acted = coordinates is not None and fill_fn(
            driver, coordinates[0], coordinates[1], text, debug
        )
    except Exception:
        acted = False

    if not acted:
        return ActionResult(
            ok=False,
            action="fill",
            match=evidence,
            reason="fill_failed",
        )

    verification = None
    if verify_image is not None:
        try:
            after = screenshot_fn(driver)
        except Exception:
            return ActionResult(
                ok=False,
                action="fill",
                match=evidence,
                reason="verification_screenshot_failed",
            )
        verification = _verification_result(
            after,
            verify_image,
            confidence if verification_confidence is None else verification_confidence,
            ambiguity_margin,
            verification_expected_visible,
        )
        if not verification.ok:
            return ActionResult(
                ok=False,
                action="fill",
                match=evidence,
                verification=verification,
                reason=verification.reason,
            )

    return ActionResult(
        ok=True,
        action="fill",
        match=evidence,
        verification=verification,
    )
