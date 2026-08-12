"""
Appium adapter for Pyxelator (Beta).

Provides simple functions to interact with mobile/desktop elements using image templates
in Appium-based automation.

Note: Appium support is currently in beta. Please report any issues on GitHub.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot, locate_match
from ..utils import explain_miss, to_css_pixels


def _get_screenshot(driver) -> bytes:
    """Get screenshot from Appium driver."""
    return driver.get_screenshot_as_png()


def _viewport_width(driver) -> Optional[float]:
    """
    Width of the driver's tap coordinate space.

    On iOS this is in points while the screenshot is in pixels (2x or 3x), so
    raw screenshot coordinates would tap well outside the intended element.
    On Android the two usually match and the resulting scale is 1.0.
    """
    try:
        return driver.get_window_size()['width']
    except Exception:
        return None


def _touch_sequence(driver):
    """
    Build a W3C touch action sequence.

    The only gesture API available. Appium-Python-Client 3.0 removed
    TouchAction, so anything built on it fails to import.
    """
    from selenium.webdriver.common.actions import interaction
    from selenium.webdriver.common.actions.action_builder import ActionBuilder
    from selenium.webdriver.common.actions.pointer_input import PointerInput

    return ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))


def _tap(driver, x: int, y: int, debug: bool = False) -> bool:
    """Tap a point in the driver's coordinate space."""
    try:
        actions = _touch_sequence(driver)
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()
        return True
    except Exception as e:
        print(f"[Pyxelator ERROR] Tap at ({x}, {y}) failed: {type(e).__name__}: {e}")
        if debug:
            print(f"[Pyxelator] Gestures use the W3C Actions protocol, which needs "
                  f"an Appium 2.0+ server")
        return False


def find_app(driver, image: str, confidence: float = 0.7, verbose: bool = False) -> bool:
    """
    Check if element exists on the screen.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise

    Example:
        from appium import webdriver
        from pyxelator import find

        caps = {
            'platformName': 'Android',
            'deviceName': 'emulator-5554',
            'app': '/path/to/app.apk'
        }
        driver = webdriver.Remote('http://localhost:4723/wd/hub', caps)

        if find(driver, 'login_button.png'):
            print("Login button found!")
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    screenshot = _get_screenshot(driver)
    result = find_image_in_screenshot(screenshot, image, confidence) is not None

    if not result and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")

    return result


def locate_app(driver, image: str, confidence: float = 0.7, verbose: bool = False) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the screen.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        (x, y) center coordinates in the driver's tap coordinate space if
        found, None otherwise. On iOS these differ from raw screenshot pixels.

    Example:
        coords = locate(driver, 'button.png')
        if coords:
            print(f"Button at position {coords}")
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return None

    screenshot = _get_screenshot(driver)
    match = locate_match(screenshot, image, confidence)
    result = None if match is None else to_css_pixels(match, _viewport_width(driver))

    if result is None and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")

    return result


def click_app(driver, image: str, confidence: float = 0.7, debug: bool = False) -> bool:
    """
    Tap element identified by image template.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        debug: Print debug information (default: False)

    Returns:
        True if tapped successfully, False if not found

    Example:
        from pyxelator import click

        click(driver, 'submit_button.png')
        click(driver, 'button.png', debug=True)
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    coords = locate_app(driver, image, confidence)
    if not coords:
        print(f"[Pyxelator ERROR] Element not found: '{image}'")
        for line in explain_miss(_get_screenshot(driver), image, confidence):
            print(f"[Pyxelator] {line}")
        return False

    if debug:
        print(f"[Pyxelator] Element found at ({coords[0]}, {coords[1]})")

    x, y = coords

    return _tap(driver, x, y, debug)


def fill_app(driver, image: str, text: str, confidence: float = 0.7, debug: bool = False) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        debug: Print debug information (default: False)

    Returns:
        True if filled successfully, False if not found

    Example:
        from pyxelator import fill

        fill(driver, 'email_field.png', 'user@example.com')
        fill(driver, 'password_field.png', 'secret123', debug=True)
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    coords = locate_app(driver, image, confidence)
    if not coords:
        print(f"[Pyxelator ERROR] Element not found: '{image}'")
        for line in explain_miss(_get_screenshot(driver), image, confidence):
            print(f"[Pyxelator] {line}")
        return False

    if debug:
        print(f"[Pyxelator] Element found at ({coords[0]}, {coords[1]})")

    x, y = coords

    # Tap to focus the field first - send_keys goes to whatever is active.
    if not _tap(driver, x, y, debug):
        return False

    # Give the on-screen keyboard time to appear and focus to settle.
    import time
    time.sleep(0.3)

    try:
        active_element = driver.switch_to.active_element
        active_element.clear()
        active_element.send_keys(text)
        return True
    except Exception as e:
        print(f"[Pyxelator ERROR] Could not type into the focused element: "
              f"{type(e).__name__}: {e}")
        if debug:
            print(f"[Pyxelator] The tap landed at ({x}, {y}) but no text field took "
                  f"focus. Your template may be matching a label rather than the "
                  f"input itself.")
        return False


SWIPE_DIRECTIONS = ('up', 'down', 'left', 'right')


def swipe_app(
    driver,
    image: str,
    direction: str = "up",
    distance: int = 200,
    confidence: float = 0.7,
    duration: float = 0.2,
    debug: bool = False
) -> bool:
    """
    Swipe starting from the element's position.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image (starting point)
        direction: Swipe direction ('up', 'down', 'left', 'right')
        distance: Swipe distance in pixels (default: 200)
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        duration: Seconds spent travelling, held between press and release
            (default: 0.2). Too fast reads as a fling rather than a drag;
            raise it if the app does not react.
        debug: Print debug information (default: False)

    Returns:
        True if swiped successfully, False if the element was not found, the
        direction is invalid, or the gesture failed

    Example:
        from pyxelator import swipe_app

        # Swipe up from the centre of the matched element
        swipe_app(driver, 'list_item.png', 'up', 300)

    Note:
        The swipe is clamped to the screen bounds - a swipe that would run off
        the edge stops at it, since drivers reject out-of-bounds coordinates.
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    if direction not in SWIPE_DIRECTIONS:
        print(f"[Pyxelator ERROR] Invalid swipe direction: '{direction}'")
        print(f"[Pyxelator] Expected one of: {', '.join(SWIPE_DIRECTIONS)}")
        return False

    coords = locate_app(driver, image, confidence)
    if not coords:
        print(f"[Pyxelator ERROR] Element not found: '{image}'")
        for line in explain_miss(_get_screenshot(driver), image, confidence):
            print(f"[Pyxelator] {line}")
        return False

    x, y = coords

    offsets = {
        'up': (0, -distance),
        'down': (0, distance),
        'left': (-distance, 0),
        'right': (distance, 0),
    }
    dx, dy = offsets[direction]
    end_x, end_y = x + dx, y + dy

    # Drivers reject off-screen coordinates
    try:
        size = driver.get_window_size()
        end_x = max(0, min(end_x, size['width'] - 1))
        end_y = max(0, min(end_y, size['height'] - 1))
    except Exception:
        pass

    if (end_x, end_y) == (x, y):
        print(f"[Pyxelator ERROR] Swipe would not move: already at the screen edge")
        return False

    if debug:
        print(f"[Pyxelator] Swiping {direction} from ({x}, {y}) to ({end_x}, {end_y})")

    try:
        actions = _touch_sequence(driver)
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(duration)
        actions.pointer_action.move_to_location(end_x, end_y)
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()
        return True
    except Exception as e:
        print(f"[Pyxelator ERROR] Swipe failed: {type(e).__name__}: {e}")
        if debug:
            print(f"[Pyxelator] Gestures use the W3C Actions protocol, which needs "
                  f"an Appium 2.0+ server")
        return False


# Alias for exists
exists_app = find_app
