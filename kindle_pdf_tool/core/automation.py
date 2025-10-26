"""Automation functionality for Kindle window control."""

import time
from typing import Optional
import pyautogui
import pygetwindow as gw
from ..utils.logger import get_logger


logger = get_logger()


class KindleAutomation:
    """Handles Kindle window detection and automation."""

    # Window title patterns to search for
    WINDOW_PATTERNS = [
        "Kindle",
        "kindle",
        "Amazon Kindle",
        "Kindle for PC"
    ]

    def __init__(self):
        """Initialize KindleAutomation."""
        self.window = None
        # Disable pyautogui fail-safe for automation
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def find_kindle_window(self) -> bool:
        """
        Find and store Kindle window.

        Returns:
            True if window found, False otherwise
        """
        for pattern in self.WINDOW_PATTERNS:
            try:
                windows = gw.getWindowsWithTitle(pattern)
                if windows:
                    self.window = windows[0]
                    logger.info(f"Found Kindle window: {self.window.title}")
                    return True
            except Exception as e:
                logger.error(f"Error searching for pattern '{pattern}': {e}")
                continue

        logger.error("Kindle window not found")
        return False

    def activate_window(self) -> bool:
        """
        Activate (bring to foreground) the Kindle window.

        Returns:
            True if successful, False otherwise
        """
        if not self.window:
            logger.error("No window to activate")
            return False

        try:
            self.window.activate()
            time.sleep(1.0)  # Wait for window to activate
            logger.info("Kindle window activated")
            return True
        except Exception as e:
            logger.error(f"Failed to activate window: {e}")
            return False

    def turn_page(self, direction: str = "right") -> bool:
        """
        Turn page in Kindle by pressing arrow key.

        Args:
            direction: "right" for next page, "left" for previous page

        Returns:
            True if successful, False otherwise
        """
        try:
            key = "right" if direction == "right" else "left"
            pyautogui.press(key)
            logger.info(f"Pressed {key} arrow key")
            return True
        except Exception as e:
            logger.error(f"Failed to turn page: {e}")
            return False

    def initialize(self) -> bool:
        """
        Initialize automation by finding and activating Kindle window.

        Returns:
            True if successful, False otherwise
        """
        if not self.find_kindle_window():
            return False

        if not self.activate_window():
            return False

        return True

    def is_window_active(self) -> bool:
        """
        Check if Kindle window is still active.

        Returns:
            True if window exists and is active, False otherwise
        """
        if not self.window:
            return False

        try:
            # Check if window still exists
            return self.window.isActive
        except Exception:
            return False
