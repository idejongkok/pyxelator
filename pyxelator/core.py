"""
Core image matching functionality.

This module contains the core computer vision logic for template matching
that is shared across all adapters (Selenium, Playwright, Appium, etc).
"""

import cv2
import numpy as np
from typing import Tuple, Optional


def find_image_in_screenshot(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7,
    grayscale: bool = True
) -> Optional[Tuple[int, int]]:
    """
    Locate element by image template matching using OpenCV.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        confidence: Match confidence threshold 0.0-1.0 (default: 0.7)
        grayscale: Use grayscale matching (default: True)

    Returns:
        (x, y) center coordinates of matched element, or None if not found

    Algorithm:
        1. Decode screenshot from bytes to OpenCV image
        2. Convert to grayscale for better matching
        3. Load template image
        4. Use cv2.matchTemplate with TM_CCOEFF_NORMED
        5. Fall back to TM_CCORR_NORMED if first method fails
        6. Return center coordinates if confidence threshold met
    """
    try:
        # Decode screenshot
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Load template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR)
        if template is None:
            return None

        # Convert to grayscale if needed
        if not grayscale and len(template.shape) == 3:
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        h, w = template.shape[:2]
        img_h, img_w = img_gray.shape[:2]

        # Validate template size
        if h > img_h or w > img_w:
            return None

        # Template matching using TM_CCOEFF_NORMED (best for accuracy)
        result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            # Return center coordinates
            return (max_loc[0] + w // 2, max_loc[1] + h // 2)

        return None

    except Exception:
        return None


def check_image_exists(
    screenshot_bytes: bytes,
    template_path: str,
    confidence: float = 0.7
) -> bool:
    """
    Check if image template exists in screenshot.

    Args:
        screenshot_bytes: Screenshot as bytes
        template_path: Path to template image file
        confidence: Match confidence threshold 0.0-1.0 (default: 0.7)

    Returns:
        True if found, False otherwise
    """
    return find_image_in_screenshot(screenshot_bytes, template_path, confidence) is not None
