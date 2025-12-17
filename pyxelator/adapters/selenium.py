"""
Selenium WebDriver adapter for Pyxelator.

Provides simple functions to interact with web elements using image templates
in Selenium-based automation.
"""

from typing import Tuple, Optional
from ..core import find_image_in_screenshot
import time


def _get_screenshot(driver) -> bytes:
    """Get screenshot from Selenium WebDriver."""
    return driver.get_screenshot_as_png()


def find(driver, image: str, confidence: float = 0.7, verbose: bool = False) -> bool:
    """
    Check if element exists on the page.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        verbose: Print warning if element not found (default: False)

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
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    screenshot = _get_screenshot(driver)
    result = find_image_in_screenshot(screenshot, image, confidence) is not None

    if not result and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template image")

    return result


def locate(driver, image: str, confidence: float = 0.7, verbose: bool = False) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the page.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        verbose: Print warning if element not found (default: False)

    Returns:
        (x, y) center coordinates if found, None otherwise

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
    result = find_image_in_screenshot(screenshot, image, confidence)

    if result is None and verbose:
        print(f"[Pyxelator WARNING] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template image")

    return result


def click(driver, image: str, confidence: float = 0.7, retries: int = 3, delay: float = 0.5, debug: bool = False) -> bool:
    """
    Click element identified by image template.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        retries: Number of retry attempts (default: 3)
        delay: Delay between retries in seconds (default: 0.5)
        debug: Print debug information (default: False)

    Returns:
        True if clicked successfully, False if not found

    Example:
        from pyxelator import click

        click(driver, 'submit_button.png')
        click(driver, 'button.png', retries=5, delay=1.0, debug=True)
    """
    # Validate template image file exists
    import os
    if not os.path.exists(image):
        error_msg = f"[Pyxelator ERROR] Template image file not found: '{image}'"
        print(error_msg)
        if debug:
            print(f"[Pyxelator] Current working directory: {os.getcwd()}")
            print(f"[Pyxelator] Tip: Use absolute path or ensure the file exists in current directory")
        return False

    for attempt in range(retries):
        coords = locate(driver, image, confidence)
        if not coords:
            if debug:
                print(f"[Pyxelator] Attempt {attempt + 1}/{retries}: Element not found in screenshot")
                if attempt == 0:  # Only show tips on first attempt
                    print(f"[Pyxelator] ")
                    print(f"[Pyxelator] The template image does not match any element on the page.")
                    print(f"[Pyxelator] Common causes:")
                    print(f"[Pyxelator]   - Template was captured at different window size (try driver.maximize_window())")
                    print(f"[Pyxelator]   - Page content has changed")
                    print(f"[Pyxelator]   - Template image is too large or captures wrong area")
                    print(f"[Pyxelator] ")
                    print(f"[Pyxelator] Solutions:")
                    print(f"[Pyxelator]   - Lower confidence: click(driver, '{image}', confidence=0.6)")
                    print(f"[Pyxelator]   - Recapture template at same window size as test")
                    print(f"[Pyxelator]   - Use smaller, more specific screenshot of just the button")
            if attempt < retries - 1:
                time.sleep(delay)
                continue

            # Final failure message
            if not debug:
                print(f"[Pyxelator ERROR] Element not found after {retries} attempts: '{image}'")
                print(f"[Pyxelator] The template image does not match the current page.")
                print(f"[Pyxelator] Try: click(driver, '{image}', debug=True) for detailed troubleshooting")
            return False

        x, y = coords
        if debug:
            print(f"[Pyxelator] Attempt {attempt + 1}/{retries}: Element found at ({x}, {y})")

        # Method 1: JavaScript click with closest() - Find actual clickable element
        try:
            script = f"""
                var el = document.elementFromPoint({x}, {y});
                if (!el) {{
                    return {{success: false, reason: 'No element at coordinates'}};
                }}

                // Find the actual clickable element
                var clickable = el.closest('button') ||
                               el.closest('a') ||
                               el.closest('[onclick]') ||
                               el.closest('[role="button"]');

                // If no clickable parent, check if element itself is clickable
                if (!clickable) {{
                    var style = window.getComputedStyle(el);
                    var isPointer = style.cursor === 'pointer';
                    var isInteractive = el.tagName === 'BUTTON' ||
                                       el.tagName === 'A' ||
                                       el.tagName === 'INPUT' ||
                                       el.tagName === 'SELECT' ||
                                       el.hasAttribute('onclick');

                    if (!isPointer && !isInteractive) {{
                        return {{
                            success: false,
                            reason: 'Element is not clickable',
                            tag: el.tagName,
                            text: (el.textContent || '').substring(0, 50)
                        }};
                    }}
                    clickable = el;
                }}

                // Click the element
                clickable.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}));
                clickable.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}));
                clickable.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                clickable.click();

                return {{success: true, tag: clickable.tagName, text: (clickable.textContent || '').substring(0, 50)}};
            """
            result = driver.execute_script(script)

            if isinstance(result, dict):
                if not result.get('success'):
                    # Element found but not clickable
                    print(f"[Pyxelator ERROR] {result.get('reason', 'Click failed')}")
                    if 'tag' in result:
                        print(f"[Pyxelator] Found: <{result['tag']}> \"{result.get('text', '')}\"")
                        print(f"[Pyxelator] This is not a clickable element (button, link, etc).")
                        print(f"[Pyxelator] Your template may be matching the wrong area of the page.")
                        print(f"[Pyxelator] Tip: Recapture a smaller screenshot focused on the actual button.")
                    return False
                else:
                    if debug:
                        print(f"[Pyxelator] SUCCESS: Clicked <{result['tag']}> \"{result.get('text', '')}\"")
                    return True

            # Old boolean return (for backward compat)
            if result:
                if debug:
                    print(f"[Pyxelator] SUCCESS: JavaScript click")
                return True

        except Exception as e:
            if debug:
                print(f"[Pyxelator] FAILED: JavaScript closest() - {e}")
            pass

        # Method 2: ActionChains - Direct coordinate click
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.move_by_offset(x, y).click().perform()
            # Reset mouse position
            actions.move_by_offset(-x, -y).perform()
            if debug:
                print(f"[Pyxelator] SUCCESS: ActionChains click at ({x}, {y})")
            return True
        except Exception as e:
            if debug:
                print(f"[Pyxelator] FAILED: ActionChains - {e}")
            pass

        # Method 3: JavaScript with scrollIntoView
        try:
            script = f"""
                var el = document.elementFromPoint({x}, {y});
                if (el) {{
                    el.scrollIntoView({{behavior: 'instant', block: 'center'}});
                    el.click();
                    return true;
                }}
                return false;
            """
            result = driver.execute_script(script)
            if debug:
                print(f"[Pyxelator] JavaScript scrollIntoView result: {result}")
            if result:
                if debug:
                    print(f"[Pyxelator] SUCCESS: JavaScript scrollIntoView click")
                return True
        except Exception as e:
            if debug:
                print(f"[Pyxelator] FAILED: JavaScript scrollIntoView - {e}")
            pass

        # Method 4: Original mouse events sequence
        try:
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
            result = driver.execute_script(script)
            if debug:
                print(f"[Pyxelator] MouseEvent sequence result: {result}")
            if result:
                if debug:
                    print(f"[Pyxelator] SUCCESS: MouseEvent sequence")
                return True
        except Exception as e:
            if debug:
                print(f"[Pyxelator] FAILED: MouseEvent sequence - {e}")
            pass

        # If all methods failed, retry
        if attempt < retries - 1:
            if debug:
                print(f"[Pyxelator] All methods failed, retrying in {delay}s...")
            time.sleep(delay)

    if debug:
        print(f"[Pyxelator] FAILED: All {retries} attempts exhausted")
    return False


def fill(driver, image: str, text: str, confidence: float = 0.7, debug: bool = False) -> bool:
    """
    Fill text into input element identified by image template.

    Args:
        driver: Selenium WebDriver instance
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)
        debug: Print debug information (default: False)

    Returns:
        True if filled successfully, False if not found

    Example:
        from pyxelator import fill

        fill(driver, 'email_field.png', 'user@example.com')
        fill(driver, 'password_field.png', 'secret123')
    """
    # Validate template image exists
    import os
    if not os.path.exists(image):
        print(f"[Pyxelator ERROR] Template image file not found: '{image}'")
        return False

    coords = locate(driver, image, confidence)
    if not coords:
        print(f"[Pyxelator ERROR] Element not found: '{image}'")
        print(f"[Pyxelator] Tip: Try lowering confidence or recapture the template")
        return False

    x, y = coords
    if debug:
        print(f"[Pyxelator] Element found at ({x}, {y})")

    # Escape text for JavaScript - handle quotes and special characters
    import json
    text_escaped = json.dumps(text)[1:-1]  # Remove surrounding quotes from json.dumps

    # Fill with React-compatible event sequence
    script = f"""
        var el = document.elementFromPoint({x}, {y});
        if (!el) {{
            return {{success: false, reason: 'No element at coordinates'}};
        }}

        // Find fillable input element
        var input = el.closest('input') ||
                   el.closest('textarea') ||
                   el.closest('[contenteditable]');

        if (!input) {{
            // Check if element itself is fillable
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

        // Focus first
        input.focus();

        // Set value
        if (input.tagName === 'INPUT') {{
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, "value"
            ).set;
            nativeInputValueSetter.call(input, "{text_escaped}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else if (input.tagName === 'TEXTAREA') {{
            var nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, "value"
            ).set;
            nativeTextAreaValueSetter.call(input, "{text_escaped}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else {{
            // For contenteditable
            input.textContent = "{text_escaped}";
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        return {{success: true, tag: input.tagName}};
    """

    result = driver.execute_script(script)

    if isinstance(result, dict):
        if not result.get('success'):
            print(f"[Pyxelator ERROR] {result.get('reason', 'Fill failed')}")
            if 'tag' in result:
                print(f"[Pyxelator] Found: <{result['tag']}> \"{result.get('text', '')}\"")
                print(f"[Pyxelator] This is not a fillable element (input, textarea, etc).")
                print(f"[Pyxelator] Your template may be matching the wrong area.")
                print(f"[Pyxelator] Tip: Recapture screenshot focused on the input field.")
            return False
        else:
            if debug:
                print(f"[Pyxelator] SUCCESS: Filled <{result['tag']}> with text")
            return True

    # Old boolean return (backward compat)
    return bool(result)


# Alias for exists
exists = find
