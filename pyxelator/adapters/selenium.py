"""
Selenium WebDriver adapter for Pyxelator.

Provides simple functions to interact with web elements using image templates
in Selenium-based automation.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot


def _get_screenshot(driver) -> bytes:
    """Get screenshot from Selenium WebDriver."""
    return driver.get_screenshot_as_png()


def find(driver, image: str, confidence: float = 0.7) -> bool:
    """
    Check if element exists on the page.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise

    Example:
        from selenium import webdriver
        from pyxelator import find

        driver = webdriver.Chrome()
        driver.get('https://example.com')

        if find(driver, 'login_button.png'):
            print("Login button found!")
    """
    screenshot = _get_screenshot(driver)
    return find_image_in_screenshot(screenshot, image, confidence) is not None


def locate(driver, image: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the page.

    Args:
        driver: Selenium WebDriver instance
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


def click(driver, image: str, confidence: float = 0.7) -> bool:
    """
    Click element identified by image template.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if clicked successfully, False if not found

    Example:
        from pyxelator import click

        click(driver, 'submit_button.png')
    """
    coords = locate(driver, image, confidence)
    if not coords:
        return False

    x, y = coords

    script = f"""
        var el = document.elementFromPoint({x}, {y});
        if (el) {{
            // Trigger mouse events for better compatibility
            el.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window }}));
            el.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window }}));
            el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));

            // Also trigger native click for form submissions
            el.click();
            return true;
        }}
        return false;
    """
    return driver.execute_script(script)


def fill(driver, image: str, text: str, confidence: float = 0.7) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        driver: Selenium WebDriver instance
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
    coords = locate(driver, image, confidence)
    if not coords:
        return False

    x, y = coords

    # Escape text for JavaScript - handle quotes and special characters
    import json
    text_escaped = json.dumps(text)[1:-1]  # Remove surrounding quotes from json.dumps

    # Fill with React-compatible event sequence
    script = f"""
        var el = document.elementFromPoint({x}, {y});
        if (el) {{
            // Focus first
            el.focus();

            // Get React internal instance (for React 16+)
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;

            // Set value using native setter (bypasses React)
            nativeInputValueSetter.call(el, "{text_escaped}");

            // Trigger input event with React-compatible properties
            var event = new Event('input', {{ bubbles: true }});
            el.dispatchEvent(event);

            // Also trigger change event
            var changeEvent = new Event('change', {{ bubbles: true }});
            el.dispatchEvent(changeEvent);

            return true;
        }}
        return false;
    """
    return driver.execute_script(script)


# Alias for exists
exists = find
