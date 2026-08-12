"""
Unit tests for the Appium adapter.

No device or Appium server is needed: gestures go through Selenium's
ActionBuilder, whose perform() ends in driver.execute(command, payload). A fake
driver captures that payload, so the exact W3C gesture can be asserted.
"""

import cv2
import numpy as np
import pytest

from pyxelator.adapters import appium as appium_adapter
from pyxelator.adapters.appium import click_app, fill_app, locate_app, swipe_app


SCREEN_W, SCREEN_H = 480, 800
EL_X, EL_Y, EL_W, EL_H = 200, 400, 80, 40
EL_CENTER = (EL_X + EL_W // 2, EL_Y + EL_H // 2)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeDriver:
    """Records W3C action payloads instead of talking to a device."""

    __module__ = 'appium.webdriver.webdriver'

    def __init__(self, screenshot, width=SCREEN_W, height=SCREEN_H,
                 active_element=None):
        self._screenshot = screenshot
        self._size = {'width': width, 'height': height}
        self.calls = []
        self.switch_to = _SwitchTo(active_element)

    def get_screenshot_as_png(self):
        return self._screenshot

    def get_window_size(self):
            return self._size

    def execute(self, command, payload=None):
        self.calls.append((command, payload))

    # -- helpers for assertions ------------------------------------------

    @property
    def gestures(self):
        """Flattened pointer actions from the single recorded gesture."""
        assert len(self.calls) == 1, f"expected 1 gesture, got {len(self.calls)}"
        pointers = self.calls[0][1]['actions']
        assert len(pointers) == 1, "expected a single pointer device"
        return pointers[0]

    @property
    def steps(self):
        return self.gestures['actions']

    def moves(self):
        return [(s['x'], s['y']) for s in self.steps if s['type'] == 'pointerMove']


class _SwitchTo:
    def __init__(self, active_element):
        self._active = active_element

    @property
    def active_element(self):
        if self._active is None:
            raise RuntimeError("no element has focus")
        return self._active


class FakeField:
    def __init__(self):
        self.cleared = False
        self.typed = None

    def clear(self):
        self.cleared = True

    def send_keys(self, text):
        self.typed = text


@pytest.fixture
def screen():
    """A 'device screen' with a distinct element at a known position."""
    rng = np.random.default_rng(3)
    page = np.full((SCREEN_H, SCREEN_W, 3), 240, np.uint8)
    page[EL_Y:EL_Y + EL_H, EL_X:EL_X + EL_W] = rng.integers(
        0, 256, size=(EL_H, EL_W, 3), dtype=np.uint8
    )
    return page


@pytest.fixture
def screenshot(screen):
    return cv2.imencode('.png', screen)[1].tobytes()


@pytest.fixture
def template(tmp_path, screen):
    path = tmp_path / "element.png"
    cv2.imwrite(str(path), screen[EL_Y:EL_Y + EL_H, EL_X:EL_X + EL_W])
    return str(path)


@pytest.fixture
def driver(screenshot):
    return FakeDriver(screenshot)


# ---------------------------------------------------------------------------
# Regression: the whole gesture layer was built on a deleted module
# ---------------------------------------------------------------------------

def test_adapter_does_not_import_touchaction():
    """
    Regression: client 3.0 removed appium.webdriver.common.touch_action.
    swipe_app was built on it and returned False every time, and the fallbacks
    in click_app/fill_app swallowed the real W3C error.
    """
    import inspect

    source = inspect.getsource(appium_adapter)

    assert 'common.touch_action' not in source, "importing a module deleted in 3.0"
    assert 'TouchAction(' not in source, "instantiating a class that no longer exists"


def test_swipe_app_is_importable_from_the_package_root():
    """
    Regression test: swipe_app's own docstring told users to do this, but it was
    never re-exported, so the documented import raised ImportError.
    """
    from pyxelator import swipe_app as exported

    assert exported is swipe_app


# ---------------------------------------------------------------------------
# swipe_app: gesture shape
# ---------------------------------------------------------------------------

def test_swipe_uses_a_touch_pointer(driver, template):
    assert swipe_app(driver, template, 'up', 150) is True
    assert driver.gestures['parameters']['pointerType'] == 'touch'


def test_swipe_presses_moves_then_releases(driver, template):
    swipe_app(driver, template, 'up', 150)

    kinds = [s['type'] for s in driver.steps]

    assert kinds.index('pointerDown') < kinds.index('pointerUp')
    # A move before the press positions the finger; a move after it drags.
    assert kinds.index('pointerMove') < kinds.index('pointerDown')
    assert any(k == 'pointerMove' for k in kinds[kinds.index('pointerDown'):])


def test_swipe_starts_at_the_element_centre(driver, template):
    swipe_app(driver, template, 'up', 150)

    assert driver.moves()[0] == EL_CENTER


@pytest.mark.parametrize(
    "direction, expected_offset",
    [
        ('up', (0, -150)),
        ('down', (0, 150)),
        ('left', (-150, 0)),
        ('right', (150, 0)),
    ],
)
def test_swipe_direction_sets_the_end_point(driver, template, direction, expected_offset):
    swipe_app(driver, template, direction, 150)

    dx, dy = expected_offset
    assert driver.moves()[-1] == (EL_CENTER[0] + dx, EL_CENTER[1] + dy)


def test_swipe_duration_is_held_between_press_and_release(driver, template):
    swipe_app(driver, template, 'up', 150, duration=0.5)

    kinds = [s['type'] for s in driver.steps]
    pauses = [s['duration'] for s in driver.steps if s['type'] == 'pause']

    assert 500 in pauses, "duration should reach the driver in milliseconds"
    assert kinds.index('pointerDown') < kinds.index('pause') < kinds.index('pointerUp')


# ---------------------------------------------------------------------------
# swipe_app: bounds and validation
# ---------------------------------------------------------------------------

def test_swipe_is_clamped_to_the_screen(driver, template):
    """Drivers reject off-screen coordinates, so an over-long swipe is clamped."""
    assert swipe_app(driver, template, 'down', 10_000) is True

    end_x, end_y = driver.moves()[-1]
    assert 0 <= end_x < SCREEN_W
    assert 0 <= end_y < SCREEN_H


def test_swipe_that_cannot_move_is_refused(screenshot, template):
    """
    An element already at the edge cannot be swiped further that way. Clamping
    would collapse start and end onto the same point - a gesture that silently
    does nothing, which is worse than saying so.
    """
    driver = FakeDriver(screenshot, height=EL_CENTER[1] + 1)

    assert swipe_app(driver, template, 'down', 200) is False
    assert driver.calls == []


@pytest.mark.parametrize("direction", ['UP', 'sideways', 'north', ''])
def test_invalid_direction_never_reaches_the_driver(
    driver, template, direction
):
    assert swipe_app(driver, template, direction) is False
    assert driver.calls == []


def test_missing_template_takes_no_screenshot(driver, tmp_path):
    assert swipe_app(driver, str(tmp_path / "nope.png"), 'up') is False
    assert driver.calls == []


def test_swipe_returns_false_when_the_element_is_absent(driver, tmp_path):
    rng = np.random.default_rng(777)
    path = tmp_path / "absent.png"
    cv2.imwrite(str(path), rng.integers(0, 256, size=(EL_H, EL_W, 3), dtype=np.uint8))

    assert swipe_app(driver, str(path), 'up') is False
    assert driver.calls == []


def test_swipe_reports_driver_failure(driver, template):
    def boom(command, payload=None):
        raise RuntimeError("W3C actions not supported")

    driver.execute = boom

    assert swipe_app(driver, template, 'up') is False


# ---------------------------------------------------------------------------
# click_app / fill_app
# ---------------------------------------------------------------------------

def test_click_taps_the_element_centre(driver, template):
    assert click_app(driver, template) is True
    assert driver.moves() == [EL_CENTER]


def test_click_reports_driver_failure(driver, template):
    def boom(command, payload=None):
        raise RuntimeError("W3C actions not supported")

    driver.execute = boom

    assert click_app(driver, template) is False


def test_fill_taps_then_types(screenshot, template):
    field = FakeField()
    driver = FakeDriver(screenshot, active_element=field)

    assert fill_app(driver, template, "hello@example.com") is True
    assert driver.moves() == [EL_CENTER]
    assert field.cleared is True
    assert field.typed == "hello@example.com"


def test_fill_fails_when_nothing_takes_focus(driver, template):
    """The tap landed but no text field focused - report it, do not claim success."""
    assert fill_app(driver, template, "text") is False


# ---------------------------------------------------------------------------
# Coordinate space (iOS screenshots are larger than the tap space)
# ---------------------------------------------------------------------------

def test_tap_coordinates_are_scaled_to_the_tap_space(screen, template):
    """
    An iOS screenshot is 2-3x the point-based tap space. The tap must land in
    points, not screenshot pixels.
    """
    retina = cv2.resize(screen, (SCREEN_W * 2, SCREEN_H * 2),
                        interpolation=cv2.INTER_CUBIC)
    driver = FakeDriver(cv2.imencode('.png', retina)[1].tobytes(),
                        width=SCREEN_W, height=SCREEN_H)

    # The template is at 1x, the screenshot at 2x: the scale ladder finds it.
    assert click_app(driver, template) is True

    tap_x, tap_y = driver.moves()[0]
    assert abs(tap_x - EL_CENTER[0]) <= 6
    assert abs(tap_y - EL_CENTER[1]) <= 6


def test_locate_reports_tap_space_coordinates(screen, template):
    retina = cv2.resize(screen, (SCREEN_W * 2, SCREEN_H * 2),
                        interpolation=cv2.INTER_CUBIC)
    driver = FakeDriver(cv2.imencode('.png', retina)[1].tobytes(),
                        width=SCREEN_W, height=SCREEN_H)

    coords = locate_app(driver, template)

    assert coords is not None
    assert abs(coords[0] - EL_CENTER[0]) <= 6
    assert abs(coords[1] - EL_CENTER[1]) <= 6
