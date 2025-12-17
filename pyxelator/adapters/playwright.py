"""
Playwright adapter for Pyxelator.

Provides simple functions to interact with web elements using image templates
in Playwright-based automation.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot
import time


def _get_screenshot(page) -> bytes:
    """Get screenshot from Playwright Page."""
    return page.screenshot()


def find_pw(page, image: str, confidence: float = 0.7, verbose: bool = False) -> bool:
    """
    Check if element exists on the page.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        verbose: Print warning if element not found (default: False)

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
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    screenshot = _get_screenshot(page)
    result = find_image_in_screenshot(screenshot, image, confidence) is not None

    if not result and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template image")

    return result


def locate_pw(page, image: str, confidence: float = 0.7, verbose: bool = False) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the page.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        verbose: Print warning if element not found (default: False)

    Returns:
        (x, y) center coordinates if found, None otherwise

    Example:
        coords = locate_pw(page, 'button.png')
        if coords:
            print(f"Button at position {coords}")
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return None

    screenshot = _get_screenshot(page)
    result = find_image_in_screenshot(screenshot, image, confidence)

    if result is None and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template image")

    return result


def click_pw(page, image: str, confidence: float = 0.7, retries: int = 3, delay: float = 0.5, debug: bool = False) -> bool:
    """
    Click element identified by image template.

    Args:
        page: Playwright Page instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        retries: Number of retry attempts (default: 3)
        delay: Delay between retries in seconds (default: 0.5)
        debug: Print debug information (default: False)

    Returns:
        True if clicked successfully, False if not found

    Example:
        from pyxelator import click_pw

        click_pw(page, 'submit_button.png')
        click_pw(page, 'button.png', debug=True)
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        if debug:
            print(f"[Pyxelator] Current working directory: {os.getcwd()}")
        return False

    for attempt in range(retries):
        coords = locate_pw(page, image, confidence)
        if not coords:
            if debug:
                print(f"[Pyxelator] Attempt {attempt + 1}/{retries}: Element not found in screenshot")
                if attempt == 0:
                    print(f"[Pyxelator] The template image does not match any element on the page.")
                    print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template")
            if attempt < retries - 1:
                time.sleep(delay)
                continue

            if not debug:
                print(f"[Pyxelator ERROR] Element not found after {retries} attempts: '{image}'")
                print(f"[Pyxelator] Try: click_pw(page, '{image}', debug=True) for troubleshooting")
            return False

        x, y = coords
        if debug:
            print(f"[Pyxelator] Attempt {attempt + 1}/{retries}: Element found at ({x}, {y})")

        script = f"""() => {{
            var el = document.elementFromPoint({x}, {y});
            if (!el) {{
                return {{success: false, reason: 'No element at coordinates'}};
            }}

            // Find clickable element
            var clickable = el.closest('button') ||
                           el.closest('a') ||
                           el.closest('[onclick]') ||
                           el.closest('[role="button"]');

            if (!clickable) {{
                var style = window.getComputedStyle(el);
                var isClickable = el.tagName === 'BUTTON' ||
                                 el.tagName === 'A' ||
                                 el.hasAttribute('onclick') ||
                                 style.cursor === 'pointer';

                if (!isClickable) {{
                    return {{
                        success: false,
                        reason: 'Element is not clickable',
                        tag: el.tagName,
                        text: (el.textContent || '').substring(0, 50)
                    }};
                }}
                clickable = el;
            }}

            // Click
            clickable.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}));
            clickable.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}));
            clickable.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
            clickable.click();

            return {{success: true, tag: clickable.tagName, text: (clickable.textContent || '').substring(0, 50)}};
        }}"""

        result = page.evaluate(script)

        if isinstance(result, dict):
            if not result.get('success'):
                print(f"[Pyxelator ERROR] {result.get('reason', 'Click failed')}")
                if 'tag' in result:
                    print(f"[Pyxelator] Found: <{result['tag']}> \"{result.get('text', '')}\"")
                    print(f"[Pyxelator] This is not a clickable element.")
                    print(f"[Pyxelator] Tip: Recapture a smaller screenshot focused on the button.")
                return False
            else:
                if debug:
                    print(f"[Pyxelator] SUCCESS: Clicked <{result['tag']}> \"{result.get('text', '')}\"")
                return True

        if result:
            if debug:
                print(f"[Pyxelator] SUCCESS: Click completed")
            return True

        if attempt < retries - 1:
            if debug:
                print(f"[Pyxelator] Click failed, retrying in {delay}s...")
            time.sleep(delay)

    return False


def fill_pw(page, image: str, text: str, confidence: float = 0.7, debug: bool = False) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        page: Playwright Page instance
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        debug: Print debug information (default: False)

    Returns:
        True if filled successfully, False if not found

    Example:
        from pyxelator import fill_pw

        fill_pw(page, 'email_field.png', 'user@example.com')
        fill_pw(page, 'password_field.png', 'secret123', debug=True)
    """
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    coords = locate_pw(page, image, confidence)
    if not coords:
        print(f"[Pyxelator ERROR] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template")
        return False

    x, y = coords
    if debug:
        print(f"[Pyxelator] Element found at ({x}, {y})")

    # Escape text for JavaScript
    import json
    text_escaped = json.dumps(text)[1:-1]

    # Fill with React-compatible event sequence
    script = f"""() => {{
        var el = document.elementFromPoint({x}, {y});
        if (!el) {{
            return {{success: false, reason: 'No element at coordinates'}};
        }}

        // Find fillable element
        var input = el.closest('input') ||
                   el.closest('textarea') ||
                   el.closest('[contenteditable]');

        if (!input) {{
            if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA' && !el.hasAttribute('contenteditable')) {{
                return {{
                    success: false,
                    reason: 'Element is not fillable',
                    tag: el.tagName,
                    text: (el.textContent || '').substring(0, 50)
                }};
            }}
            input = el;
        }}

        // Focus
        input.focus();

        // Set value
        if (input.tagName === 'INPUT') {{
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            setter.call(input, "{text_escaped}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else if (input.tagName === 'TEXTAREA') {{
            var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            setter.call(input, "{text_escaped}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else {{
            input.textContent = "{text_escaped}";
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        return {{success: true, tag: input.tagName}};
    }}"""

    result = page.evaluate(script)

    if isinstance(result, dict):
        if not result.get('success'):
            print(f"[Pyxelator ERROR] {result.get('reason', 'Fill failed')}")
            if 'tag' in result:
                print(f"[Pyxelator] Found: <{result['tag']}> \"{result.get('text', '')}\"")
                print(f"[Pyxelator] This is not a fillable element.")
                print(f"[Pyxelator] Tip: Recapture screenshot focused on the input field.")
            return False
        else:
            if debug:
                print(f"[Pyxelator] SUCCESS: Filled <{result['tag']}> with text")
            return True

    return bool(result)


# Alias for exists
exists_pw = find_pw
