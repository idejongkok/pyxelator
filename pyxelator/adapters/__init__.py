"""
Adapters for different automation frameworks.

This package contains adapters for:
- Selenium WebDriver (web automation)
- Playwright (web automation)
- Appium (mobile/desktop automation) - Beta
"""

from .selenium import find, locate, click, fill, exists
from .playwright import find_pw, locate_pw, click_pw, fill_pw, exists_pw
from .appium import find_app, locate_app, click_app, fill_app, exists_app, swipe_app

__all__ = [
    # Selenium adapter
    'find', 'locate', 'click', 'fill', 'exists',
    # Playwright adapter
    'find_pw', 'locate_pw', 'click_pw', 'fill_pw', 'exists_pw',
    # Appium adapter
    'find_app', 'locate_app', 'click_app', 'fill_app', 'exists_app', 'swipe_app',
]
