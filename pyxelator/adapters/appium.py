"""
Appium adapter for Pyxelator (Beta).

Provides simple functions to interact with mobile/desktop elements using image templates
in Appium-based automation.

Note: Appium support is currently in beta. Please report any issues on GitHub.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot


def _get_screenshot(driver) -> bytes:
    """Get screenshot from Appium driver."""
    return driver.get_screenshot_as_png()


def find_app(driver, image: str, confidence: float = 0.7) -> bool:
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
    screenshot = _get_screenshot(driver)
    return find_image_in_screenshot(screenshot, image, confidence) is not None


def locate_app(driver, image: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the screen.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        (x, y) center coordinates if found, None otherwise

    Example:
        coords = locate(driver, 'button.png')
        if coords:
            print(f"Button at position {coords}")
    """
    screenshot = _get_screenshot(driver)
    return find_image_in_screenshot(screenshot, image, confidence)


def click_app(driver, image: str, confidence: float = 0.7) -> bool:
    """
    Tap element identified by image template.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if tapped successfully, False if not found

    Example:
        from pyxelator import click

        click(driver, 'submit_button.png')
    """
    coords = locate_app(driver, image, confidence)
    if not coords:
        return False

    x, y = coords

    try:
        # Modern W3C Actions API (Appium 2.0+)
        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput

        actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()
        return True
    except Exception:
        # Fallback to legacy TouchAction API (Appium 1.x)
        try:
            from appium.webdriver.common.touch_action import TouchAction

            action = TouchAction(driver)
            action.tap(x=x, y=y).perform()
            return True
        except Exception:
            return False


def fill_app(driver, image: str, text: str, confidence: float = 0.7) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if filled successfully, False if not found

    Example:
        from pyxelator import fill

        fill(driver, 'email_field.png', 'user@example.com')
        fill(driver, 'password_field.png', 'secret123')
    """
    coords = locate_app(driver, image, confidence)
    if not coords:
        return False

    x, y = coords

    try:
        # Modern W3C Actions API for tap
        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput

        actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()

        # Small delay for keyboard to appear
        import time
        time.sleep(0.3)

        # Send keys to active element
        active_element = driver.switch_to.active_element
        active_element.clear()
        active_element.send_keys(text)
        return True
    except Exception:
        # Fallback to legacy TouchAction API
        try:
            from appium.webdriver.common.touch_action import TouchAction
            import time

            # Tap to focus
            action = TouchAction(driver)
            action.tap(x=x, y=y).perform()

            # Small delay for keyboard to appear
            time.sleep(0.3)

            # Send keys to active element
            active_element = driver.switch_to.active_element
            active_element.clear()
            active_element.send_keys(text)
            return True
        except Exception:
            return False


def swipe_app(driver, image: str, direction: str = "up", distance: int = 200, confidence: float = 0.7) -> bool:
    """
    Swipe from element position.

    Args:
        driver: Appium WebDriver instance
        image: Path to template image (starting point)
        direction: Swipe direction ('up', 'down', 'left', 'right')
        distance: Swipe distance in pixels (default: 200)
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if swiped successfully, False if not found

    Example:
        from pyxelator import swipe_app

        # Swipe up from center of image
        swipe_app(driver, 'list_item.png', 'up', 300)
    """
    coords = locate_app(driver, image, confidence)
    if not coords:
        return False

    x, y = coords

    # Calculate end point based on direction
    direction_map = {
        'up': (x, y - distance),
        'down': (x, y + distance),
        'left': (x - distance, y),
        'right': (x + distance, y)
    }

    if direction not in direction_map:
        return False

    end_x, end_y = direction_map[direction]

    try:
        from appium.webdriver.common.touch_action import TouchAction

        action = TouchAction(driver)
        action.press(x=x, y=y).wait(100).move_to(x=end_x, y=end_y).release().perform()
        return True
    except Exception:
        return False


# Alias for exists
exists_app = find_app
