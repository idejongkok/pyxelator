"""Run the structured Pyxelator flow without a browser or network.

This example generates a screenshot/template pair, then uses a small
Playwright-shaped recording page to demonstrate the same public calls used
with a real Playwright Page. Replace ``RecordingPage`` with your framework
driver and keep the result handling unchanged.
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyxelator import (
    ActionResult,
    MatchResult,
    click_result,
    fill_result,
    match_result,
)


class RecordingMouse:
    def __init__(self) -> None:
        self.clicks = []

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))


class RecordingPage:
    """Minimum Playwright-shaped page used only by this offline example."""

    __module__ = "playwright.sync_api._generated"

    def __init__(self, screenshot: bytes, width: int) -> None:
        self._screenshot = screenshot
        self._width = width
        self.mouse = RecordingMouse()
        self.fill_scripts = []

    def screenshot(self) -> bytes:
        return self._screenshot

    def evaluate(self, script: str):
        if script == "() => window.innerWidth":
            return self._width
        self.fill_scripts.append(script)
        return {"success": True}


def png_bytes(image: np.ndarray) -> bytes:
    encoded, buffer = cv2.imencode(".png", image)
    if not encoded:
        raise RuntimeError("could not encode generated screenshot")
    return buffer.tobytes()


def generated_images(directory: Path, *, repeated: bool = False):
    rng = np.random.default_rng(20261005)
    template = rng.integers(0, 256, size=(20, 30, 3), dtype=np.uint8)
    screenshot = np.full((100, 160, 3), 240, dtype=np.uint8)
    screenshot[20:40, 15:45] = template
    if repeated:
        screenshot[60:80, 110:140] = template

    template_path = directory / ("repeated.png" if repeated else "target.png")
    if not cv2.imwrite(str(template_path), template):
        raise RuntimeError("could not write generated template")
    return png_bytes(screenshot), str(template_path)


def main() -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        screenshot, template = generated_images(directory)

        match: MatchResult = match_result(screenshot, template, confidence=0.80)
        print("match:", match.ok, match.coordinates, round(match.score or 0.0, 3))

        click_page = RecordingPage(screenshot, width=160)
        clicked: ActionResult = click_result(click_page, template, confidence=0.80)
        print("click:", clicked.ok, click_page.mouse.clicks)

        fill_page = RecordingPage(screenshot, width=160)
        filled: ActionResult = fill_result(
            fill_page, template, "user@example.com", confidence=0.80
        )
        print("fill:", filled.ok, "writes=", len(fill_page.fill_scripts))

        repeated_screenshot, repeated_template = generated_images(
            directory, repeated=True
        )
        unsafe_page = RecordingPage(repeated_screenshot, width=160)
        refused = click_result(unsafe_page, repeated_template, confidence=0.80)
        print(
            "ambiguous:",
            refused.ok,
            refused.reason,
            "clicks=",
            unsafe_page.mouse.clicks,
        )


if __name__ == "__main__":
    main()
