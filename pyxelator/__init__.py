"""
Pyxelator - Pixel-based Element Locator
========================================

Visual element automation for Selenium, Playwright & Appium.
No more XPath hunting - just use screenshots!

Universal API - Works with any automation framework:
    from pyxelator import find, click, fill

    # Works with Selenium
    from selenium import webdriver
    driver = webdriver.Chrome()
    click(driver, 'button.png')

    # Works with Playwright
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        click(page, 'button.png')  # Same API!

    # Works with Appium (Beta)
    from appium import webdriver
    driver = webdriver.Remote(...)
    click(driver, 'button.png')  # Same API!

Note: Appium support is currently in beta.

Author: Aria Uno Suseno (@idejongkok)
Version: 0.3.1
License: MIT
"""

from typing import Tuple, Optional
from .utils import detect_driver_type

# Import adapters
from . import adapters

# Import core for advanced usage
from .core import find_image_in_screenshot, check_image_exists

__version__ = '0.3.1'
__author__ = 'Aria Uno Suseno'
__email__ = 'contact@idejongkok.com'

# Public API
__all__ = [
    # Universal API (recommended)
    'find',
    'locate',
    'click',
    'fill',
    'exists',

    # Advanced/Core functions
    'find_image_in_screenshot',
    'check_image_exists',

    # Legacy
    'Pyxelator',
]


# =============================================================================
# UNIVERSAL API - Auto-detects driver type (Selenium/Playwright/Appium)
# =============================================================================

def find(driver, image: str, confidence: float = 0.7) -> bool:
    """
    Check if element exists on the page.

    Universal function that works with Selenium, Playwright, and Appium.
    Automatically detects the driver type.

    Args:
        driver: Selenium WebDriver, Playwright Page, or Appium driver
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise

    Examples:
        # Selenium
        from selenium import webdriver
        driver = webdriver.Chrome()
        if find(driver, 'button.png'):
            print("Found!")

        # Playwright
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            page = p.chromium.launch().new_page()
            if find(page, 'button.png'):
                print("Found!")
    """
    driver_type = detect_driver_type(driver)

    if driver_type == 'playwright':
        return adapters.playwright.find_pw(driver, image, confidence)
    elif driver_type == 'appium':
        return adapters.appium.find_app(driver, image, confidence)
    else:  # selenium
        return adapters.selenium.find(driver, image, confidence)


def locate(driver, image: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
    """
    Get element coordinates on the page.

    Universal function that works with Selenium, Playwright, and Appium.
    Automatically detects the driver type.

    Args:
        driver: Selenium WebDriver, Playwright Page, or Appium driver
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        (x, y) center coordinates if found, None otherwise

    Example:
        coords = locate(driver, 'button.png')
        if coords:
            print(f"Button at position {coords}")
    """
    driver_type = detect_driver_type(driver)

    if driver_type == 'playwright':
        return adapters.playwright.locate_pw(driver, image, confidence)
    elif driver_type == 'appium':
        return adapters.appium.locate_app(driver, image, confidence)
    else:  # selenium
        return adapters.selenium.locate(driver, image, confidence)


def click(driver, image: str, confidence: float = 0.7) -> bool:
    """
    Click element identified by image template.

    Universal function that works with Selenium, Playwright, and Appium.
    Automatically detects the driver type.

    Args:
        driver: Selenium WebDriver, Playwright Page, or Appium driver
        image: Path to template image
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if clicked successfully, False if not found

    Example:
        # Same code works for Selenium, Playwright, or Appium!
        click(driver, 'submit_button.png')
    """
    driver_type = detect_driver_type(driver)

    if driver_type == 'playwright':
        return adapters.playwright.click_pw(driver, image, confidence)
    elif driver_type == 'appium':
        return adapters.appium.click_app(driver, image, confidence)
    else:  # selenium
        return adapters.selenium.click(driver, image, confidence)


def fill(driver, image: str, text: str, confidence: float = 0.7) -> bool:
    """
    Fill text into input element identified by image template.

    Universal function that works with Selenium, Playwright, and Appium.
    Automatically detects the driver type.

    Args:
        driver: Selenium WebDriver, Playwright Page, or Appium driver
        image: Path to template image
        text: Text to fill into the element
        confidence: Match confidence 0.0-1.0 (default: 0.7)

    Returns:
        True if filled successfully, False if not found

    Example:
        # Same code works for Selenium, Playwright, or Appium!
        fill(driver, 'email_field.png', 'user@example.com')
        fill(driver, 'password_field.png', 'secret123')
    """
    driver_type = detect_driver_type(driver)

    if driver_type == 'playwright':
        return adapters.playwright.fill_pw(driver, image, text, confidence)
    elif driver_type == 'appium':
        return adapters.appium.fill_app(driver, image, text, confidence)
    else:  # selenium
        return adapters.selenium.fill(driver, image, text, confidence)


# Alias
exists = find


# =============================================================================
# LEGACY CLASS - Kept for backward compatibility
# =============================================================================

class Pyxelator:
    """
    Legacy wrapper class for visual element detection.

    Note: This class is kept for backward compatibility only.
    For new code, use the module-level functions instead:
    - find(driver, image)
    - click(driver, image)
    - fill(driver, image, text)

    These functions work universally with Selenium, Playwright, and Appium!
    """

    def __init__(self, driver):
        """Initialize with any automation driver"""
        self.driver = driver

    def find(self, image: str, confidence: float = 0.7) -> bool:
        """Check if element exists"""
        return find(self.driver, image, confidence)

    def locate(self, image: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
        """Get element coordinates"""
        return locate(self.driver, image, confidence)

    def click(self, image: str, confidence: float = 0.7) -> bool:
        """Click element"""
        return click(self.driver, image, confidence)

    def fill(self, image: str, text: str, confidence: float = 0.7) -> bool:
        """Fill text into element"""
        return fill(self.driver, image, text, confidence)
