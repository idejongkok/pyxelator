"""
Playwright adapter for Pyxelator.

Provides simple functions to interact with web elements using image templates
in Playwright-based automation.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot


def _get_screenshot(page) -> bytes:
    """Get screenshot from Playwright Page."""
    return page.screenshot()


def find_pw(page, image: str, confidence: float = 0.7) -> bool:
    """
    Check if element exists on the page.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise

    Example:
        from playwright.sync_api import sync_playwright
        from pyxelator import find_pw

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto('https://example.com')

            if find_pw(page, 'login_button.png'):
                print("Login button found!")
    """
    screenshot = _get_screenshot(page)
    return find_image_in_screenshot(screenshot, image, confidence) is not None


def locate_pw(page, image: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the page.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        (x, y) center coordinates if found, None otherwise

    Example:
        coords = locate_pw(page, 'button.png')
        if coords:
            print(f"Button at position {coords}")
    """
    screenshot = _get_screenshot(page)
    return find_image_in_screenshot(screenshot, image, confidence)


def click_pw(page, image: str, confidence: float = 0.7) -> bool:
    """
    Click element identified by image template.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if clicked successfully, False if not found

    Example:
        from pyxelator import click_pw

        click_pw(page, 'submit_button.png')
    """
    coords = locate_pw(page, image, confidence)
    if not coords:
        return False

    x, y = coords

    script = f"""() => {{
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
    }}"""
    return page.evaluate(script)


def fill_pw(page, image: str, text: str, confidence: float = 0.7) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        page: Playwright Page instance
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if filled successfully, False if not found

    Example:
        from pyxelator import fill_pw

        fill_pw(page, 'email_field.png', 'user@example.com')
        fill_pw(page, 'password_field.png', 'secret123')
    """
    coords = locate_pw(page, image, confidence)
    if not coords:
        return False

    x, y = coords

    # Escape text for JavaScript
    import json
    text_escaped = json.dumps(text)[1:-1]

    # Fill with React-compatible event sequence
    script = f"""() => {{
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
    }}"""
    return page.evaluate(script)


# Alias for exists
exists_pw = find_pw
