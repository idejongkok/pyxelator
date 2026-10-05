"""Deterministic tests for ambiguity-safe structured actions."""

import cv2
import numpy as np
import pytest

import pyxelator
from pyxelator import ActionResult, MatchResult, Rectangle, click_result, fill_result
from pyxelator.actions import _verification_result


def _encode(image):
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


def _images(tmp_path, *, repeated=False):
    rng = np.random.default_rng(91)
    template = rng.integers(0, 256, size=(20, 30, 3), dtype=np.uint8)
    screen = np.full((100, 160, 3), 240, dtype=np.uint8)
    screen[20:40, 15:45] = template
    if repeated:
        screen[60:80, 110:140] = template
    path = tmp_path / "target.png"
    cv2.imwrite(str(path), template)
    return _encode(screen), str(path)


class FakeMouse:
    def __init__(self):
        self.clicks = []

    def click(self, x, y):
        self.clicks.append((x, y))


class FakePlaywrightPage:
    __module__ = "playwright.sync_api._generated"

    def __init__(self, screenshot, width=160, write_result=None):
        self._screenshot = screenshot
        self.width = width
        self.mouse = FakeMouse()
        self.write_scripts = []
        self.write_result = {"success": True} if write_result is None else write_result

    def screenshot(self):
        return self._screenshot

    def evaluate(self, script):
        if script == "() => window.innerWidth":
            return self.width
        self.write_scripts.append(script)
        if isinstance(self.write_result, Exception):
            raise self.write_result
        return self.write_result


class FakeActiveElement:
    def __init__(self, error=None):
        self.error = error
        self.clears = 0
        self.values = []

    def clear(self):
        self.clears += 1
        if self.error:
            raise self.error

    def send_keys(self, text):
        self.values.append(text)


class FakeSwitchTo:
    def __init__(self, active_element):
        self.active_element = active_element


class FakeAppiumDriver:
    __module__ = "appium.webdriver.webdriver"

    def __init__(self, screenshot, width=160, active_error=None):
        self._screenshot = screenshot
        self.width = width
        self.calls = []
        self.active = FakeActiveElement(active_error)
        self.switch_to = FakeSwitchTo(self.active)

    def get_screenshot_as_png(self):
        return self._screenshot

    def get_window_size(self):
        return {"width": self.width, "height": 100}

    def execute(self, command, payload=None):
        self.calls.append((command, payload))


class FakeSeleniumDriver:
    """Selenium-shaped driver that records browser-side click scripts."""

    __module__ = "selenium.webdriver.remote.webdriver"

    def __init__(self, *screenshots, width=160, write_result=None):
        self.screenshots = list(screenshots)
        self.width = width
        self.screenshot_calls = 0
        self.click_scripts = []
        self.write_result = {"success": True} if write_result is None else write_result

    def get_screenshot_as_png(self):
        index = min(self.screenshot_calls, len(self.screenshots) - 1)
        self.screenshot_calls += 1
        return self.screenshots[index]

    def execute_script(self, script):
        if script == "return window.innerWidth;":
            return self.width
        self.click_scripts.append(script)
        if isinstance(self.write_result, Exception):
            raise self.write_result
        return self.write_result


def _driver_for(kind, screenshot):
    if kind == "selenium":
        return FakeSeleniumDriver(screenshot)
    if kind == "playwright":
        return FakePlaywrightPage(screenshot)
    return FakeAppiumDriver(screenshot)


def _writes(driver):
    if isinstance(driver, FakeSeleniumDriver):
        return len(driver.click_scripts)
    if isinstance(driver, FakePlaywrightPage):
        return len(driver.write_scripts) + len(driver.mouse.clicks)
    return len(driver.calls) + driver.active.clears + len(driver.active.values)


def test_click_result_acts_on_one_safe_match(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot)

    result = click_result(driver, template)

    assert isinstance(result, ActionResult)
    assert result.ok is True
    assert result.reason is None
    assert result.match is not None and result.match.coordinates == (30, 30)
    assert len(driver.click_scripts) == 1
    assert "elementFromPoint(30, 30)" in driver.click_scripts[0]


def test_click_result_dispatches_to_playwright_coordinate_click(tmp_path):
    screenshot, template = _images(tmp_path)
    page = FakePlaywrightPage(screenshot)

    result = click_result(page, template)

    assert result.ok is True
    assert page.mouse.clicks == [(30, 30)]


def test_click_result_dispatches_to_appium_touch_action(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeAppiumDriver(screenshot)

    result = click_result(driver, template)

    assert result.ok is True
    assert len(driver.calls) == 1
    steps = driver.calls[0][1]["actions"][0]["actions"]
    assert (steps[0]["x"], steps[0]["y"]) == (30, 30)


def test_click_result_refuses_below_threshold_without_acting(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot)

    result = click_result(driver, template, confidence=1.1)

    assert result.ok is False
    assert result.reason == "below_threshold"
    assert result.match is not None and result.match.score is not None
    assert driver.click_scripts == []


def test_click_result_refuses_ambiguous_match_without_acting(tmp_path):
    screenshot, template = _images(tmp_path, repeated=True)
    driver = FakeSeleniumDriver(screenshot)

    result = click_result(driver, template)

    assert result.ok is False
    assert result.reason == "ambiguous_match"
    assert result.match is not None and result.match.ambiguous is True
    assert driver.click_scripts == []


def test_click_result_can_verify_an_existing_template_after_action(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot, screenshot)

    result = click_result(driver, template, verify_image=template)

    assert result.ok is True
    assert result.verification is not None
    assert result.verification.ok is True
    assert result.verification.observed_visible is True
    assert driver.screenshot_calls == 2


def test_disappearance_verification_accepts_only_evaluated_absence(tmp_path):
    screenshot, template = _images(tmp_path)
    rng = np.random.default_rng(1234)
    absent = rng.integers(0, 256, size=(20, 30, 3), dtype=np.uint8)
    absent_path = tmp_path / "absent.png"
    cv2.imwrite(str(absent_path), absent)
    driver = FakeSeleniumDriver(screenshot, screenshot)

    result = click_result(
        driver,
        template,
        verify_image=str(absent_path),
        verification_expected_visible=False,
    )

    assert result.ok is True
    assert result.verification is not None
    assert result.verification.match is not None
    assert result.verification.match.reason == "below_threshold"


@pytest.mark.parametrize(
    "reason",
    [
        "invalid_screenshot",
        "invalid_template",
        "flat_template",
        "no_usable_scale",
        "template_too_large",
        "match_error",
    ],
)
def test_disappearance_verification_fails_closed_on_unusable_evidence(
    monkeypatch, reason
):
    evidence = MatchResult(
        ok=False,
        found=False,
        score=None,
        threshold=0.7,
        location=None,
        scale=None,
        reason=reason,
    )
    monkeypatch.setattr("pyxelator.actions.match_result", lambda *args, **kwargs: evidence)

    result = _verification_result(b"unused", "unused.png", 0.7, 0.02, False)

    assert result.ok is False
    assert result.observed_visible is False
    assert result.reason == reason


@pytest.mark.parametrize(
    ("ambiguous", "reason"),
    [(False, "unexpected_match"), (True, "ambiguous_match")],
)
def test_disappearance_verification_rejects_presence_and_ambiguity(
    monkeypatch, ambiguous, reason
):
    evidence = MatchResult(
        ok=not ambiguous,
        found=True,
        score=0.99,
        threshold=0.7,
        location=Rectangle(10, 20, 30, 40),
        scale=1.0,
        ambiguous=ambiguous,
        reason="ambiguous_match" if ambiguous else None,
    )
    monkeypatch.setattr("pyxelator.actions.match_result", lambda *args, **kwargs: evidence)

    result = _verification_result(b"unused", "unused.png", 0.7, 0.02, False)

    assert result.ok is False
    assert result.observed_visible is True
    assert result.reason == reason


def test_click_disappearance_verification_rejects_invalid_after_screenshot(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot, b"not an image")

    result = click_result(
        driver,
        template,
        verify_image=template,
        verification_expected_visible=False,
    )

    assert result.ok is False
    assert result.reason == "invalid_screenshot"
    assert result.verification is not None and result.verification.ok is False


@pytest.mark.parametrize("template_kind", ["missing", "flat"])
def test_click_disappearance_verification_rejects_unusable_template(
    tmp_path, template_kind
):
    screenshot, template = _images(tmp_path)
    verify_path = tmp_path / "verify.png"
    if template_kind == "flat":
        cv2.imwrite(str(verify_path), np.full((20, 30, 3), 100, dtype=np.uint8))
    driver = FakeSeleniumDriver(screenshot, screenshot)

    result = click_result(
        driver,
        template,
        verify_image=str(verify_path),
        verification_expected_visible=False,
    )

    assert result.ok is False
    assert result.reason == (
        "invalid_template" if template_kind == "missing" else "flat_template"
    )
    assert result.verification is not None and result.verification.ok is False


def test_fill_result_uses_validated_coordinates_on_selenium(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot)

    result = fill_result(driver, template, 'Ada "Lovelace"')

    assert result.ok is True
    assert result.action == "fill"
    assert len(driver.click_scripts) == 1
    assert "elementFromPoint(30, 30)" in driver.click_scripts[0]
    assert 'Ada \\"Lovelace\\"' in driver.click_scripts[0]


def test_fill_result_uses_validated_coordinates_on_playwright(tmp_path):
    screenshot, template = _images(tmp_path)
    page = FakePlaywrightPage(screenshot)

    result = fill_result(page, template, "hello")

    assert result.ok is True
    assert len(page.write_scripts) == 1
    assert "elementFromPoint(30, 30)" in page.write_scripts[0]
    assert page.mouse.clicks == []


def test_fill_result_uses_validated_coordinates_on_appium(tmp_path, monkeypatch):
    screenshot, template = _images(tmp_path)
    driver = FakeAppiumDriver(screenshot)
    monkeypatch.setattr("pyxelator.adapters.appium.time.sleep", lambda _: None, raising=False)

    result = fill_result(driver, template, "hello")

    assert result.ok is True
    assert len(driver.calls) == 1
    steps = driver.calls[0][1]["actions"][0]["actions"]
    assert (steps[0]["x"], steps[0]["y"]) == (30, 30)
    assert driver.active.clears == 1
    assert driver.active.values == ["hello"]


@pytest.mark.parametrize("kind", ["selenium", "playwright", "appium"])
@pytest.mark.parametrize("failure", ["ambiguous", "invalid_screenshot"])
def test_fill_result_performs_zero_writes_for_unsafe_or_unusable_targets(
    tmp_path, kind, failure
):
    screenshot, template = _images(tmp_path, repeated=failure == "ambiguous")
    if failure == "invalid_screenshot":
        screenshot = b"not an image"
    driver = _driver_for(kind, screenshot)

    result = fill_result(driver, template, "must not be written")

    assert result.ok is False
    assert result.reason == (
        "ambiguous_match" if failure == "ambiguous" else "invalid_screenshot"
    )
    assert _writes(driver) == 0


@pytest.mark.parametrize("kind", ["selenium", "playwright", "appium"])
def test_fill_result_reports_framework_write_errors(tmp_path, kind, monkeypatch):
    screenshot, template = _images(tmp_path)
    if kind == "selenium":
        driver = FakeSeleniumDriver(screenshot, write_result=RuntimeError("write failed"))
    elif kind == "playwright":
        driver = FakePlaywrightPage(screenshot, write_result=RuntimeError("write failed"))
    else:
        driver = FakeAppiumDriver(screenshot, active_error=RuntimeError("write failed"))
        monkeypatch.setattr("pyxelator.adapters.appium.time.sleep", lambda _: None, raising=False)

    result = fill_result(driver, template, "hello")

    assert result.ok is False
    assert result.reason == "fill_failed"


def test_fill_result_supports_optional_verification(tmp_path):
    screenshot, template = _images(tmp_path)
    driver = FakeSeleniumDriver(screenshot, screenshot)

    result = fill_result(driver, template, "hello", verify_image=template)

    assert result.ok is True
    assert result.verification is not None and result.verification.ok is True
    assert driver.screenshot_calls == 2


def test_fill_result_is_exported_and_available_on_wrapper(monkeypatch):
    driver = object()
    expected = ActionResult(ok=True, action="fill")
    calls = []

    def structured_fill(*args, **kwargs):
        calls.append((args, kwargs))
        return expected

    monkeypatch.setattr(pyxelator, "fill_result", structured_fill)

    result = pyxelator.Pyxelator(driver).fill_result(
        "field.png", "hello", 0.8, ambiguity_margin=0.01
    )

    assert "fill_result" in pyxelator.__all__
    assert result is expected
    assert calls == [
        ((driver, "field.png", "hello", 0.8), {"ambiguity_margin": 0.01})
    ]


def test_legacy_click_dispatch_and_v1_version(monkeypatch):
    driver = FakeSeleniumDriver(b"unused")
    calls = []

    def legacy_click(*args):
        calls.append(args)
        return True

    monkeypatch.setattr(pyxelator.adapters.selenium, "click", legacy_click)

    result = pyxelator.click(driver, "legacy.png", 0.8, 4, 0.25, True)

    assert type(result) is bool
    assert result is True
    assert calls == [(driver, "legacy.png", 0.8, 4, 0.25, True)]
    assert pyxelator.__version__ == "1.0.0"
