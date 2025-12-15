"""
Utility functions for Pyxelator.

Includes driver type detection and helper functions.
"""


def detect_driver_type(driver) -> str:
    """
    Auto-detect the type of automation driver.

    Args:
        driver: Any automation driver (Selenium, Playwright, Appium, etc.)

    Returns:
        One of: 'selenium', 'playwright', 'appium', or 'unknown'

    Detection logic:
        - Checks module name for known frameworks
        - Checks class name for Page (Playwright)
        - Checks for appium-specific attributes
    """
    # Get module and class name
    module = driver.__class__.__module__.lower()
    class_name = driver.__class__.__name__

    # Check for Playwright
    if 'playwright' in module or class_name == 'Page':
        return 'playwright'

    # Check for Appium
    if 'appium' in module:
        return 'appium'

    # Check for Selenium (default fallback)
    if 'selenium' in module:
        return 'selenium'

    # Check for WebDriver attributes (Selenium-like)
    if hasattr(driver, 'get_screenshot_as_png'):
        return 'selenium'

    # Check for Playwright attributes
    if hasattr(driver, 'screenshot') and hasattr(driver, 'evaluate'):
        return 'playwright'

    # Fallback to selenium (most common)
    return 'selenium'
