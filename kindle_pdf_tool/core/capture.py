"""Screenshot capture functionality for Kindle PDF Converter."""

import time
from pathlib import Path
from typing import List, Optional
import pyautogui
from PIL import Image
from ..utils.logger import get_logger


logger = get_logger()


class ScreenCapture:
    """Handles screenshot capture operations."""

    def __init__(self, temp_dir: Path):
        """
        Initialize ScreenCapture.

        Args:
            temp_dir: Directory to save temporary screenshots
        """
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)

    def capture_screenshot(
        self,
        page_num: int,
        shot_num: int = 1
    ) -> Optional[Path]:
        """
        Capture a single screenshot.

        Args:
            page_num: Current page number
            shot_num: Screenshot number (for multiple shots)

        Returns:
            Path to saved screenshot, or None if failed
        """
        try:
            # Take screenshot
            screenshot = pyautogui.screenshot()

            # Generate filename
            if shot_num == 1:
                filename = f"page_{page_num:04d}.png"
            else:
                filename = f"page_{page_num:04d}_shot_{shot_num}.png"

            filepath = self.temp_dir / filename

            # Save as PNG (lossless compression)
            screenshot.save(filepath, "PNG")

            logger.info(f"Screenshot saved: {filename}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None

    def capture_multiple(
        self,
        page_num: int,
        count: int,
        interval: float
    ) -> List[Path]:
        """
        Capture multiple screenshots with interval.

        Args:
            page_num: Current page number
            count: Number of screenshots to take
            interval: Interval between screenshots in seconds

        Returns:
            List of paths to saved screenshots
        """
        screenshots = []

        for i in range(1, count + 1):
            filepath = self.capture_screenshot(page_num, i)
            if filepath:
                screenshots.append(filepath)

            # Wait before next screenshot (except for last one)
            if i < count:
                time.sleep(interval)

        return screenshots

    def select_best_screenshot(self, screenshots: List[Path]) -> Optional[Path]:
        """
        Select the screenshot with the largest file size (best quality).

        Args:
            screenshots: List of screenshot paths

        Returns:
            Path to the best screenshot, or None if list is empty
        """
        if not screenshots:
            return None

        # Find largest file
        best_shot = max(screenshots, key=lambda p: p.stat().st_size)

        # Delete others
        for shot in screenshots:
            if shot != best_shot:
                try:
                    shot.unlink()
                    logger.info(f"Deleted: {shot.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {shot.name}: {e}")

        # Rename best shot to standard name
        page_num = int(best_shot.stem.split('_')[1])
        new_name = f"page_{page_num:04d}.png"
        new_path = best_shot.parent / new_name

        try:
            # Use replace() instead of rename() to overwrite if exists
            best_shot.replace(new_path)
            logger.info(f"Selected best screenshot: {new_name}")
            return new_path
        except Exception as e:
            logger.error(f"Failed to rename best screenshot: {e}")
            return best_shot

    def keep_last_screenshot(self, screenshots: List[Path]) -> Optional[Path]:
        """
        Keep only the last screenshot and delete others.

        Args:
            screenshots: List of screenshot paths

        Returns:
            Path to the last screenshot, or None if list is empty
        """
        if not screenshots:
            return None

        last_shot = screenshots[-1]

        # Delete all except last
        for shot in screenshots[:-1]:
            try:
                shot.unlink()
                logger.info(f"Deleted: {shot.name}")
            except Exception as e:
                logger.error(f"Failed to delete {shot.name}: {e}")

        # Rename last shot to standard name
        page_num = int(last_shot.stem.split('_')[1])
        new_name = f"page_{page_num:04d}.png"
        new_path = last_shot.parent / new_name

        try:
            # Use replace() instead of rename() to overwrite if exists
            last_shot.replace(new_path)
            logger.info(f"Kept last screenshot: {new_name}")
            return new_path
        except Exception as e:
            logger.error(f"Failed to rename last screenshot: {e}")
            return last_shot

    def rename_all_screenshots(self, screenshots: List[Path], page_num: int) -> List[Path]:
        """
        Rename all screenshots for multi-page mode.

        Args:
            screenshots: List of screenshot paths
            page_num: Current page number

        Returns:
            List of renamed paths
        """
        renamed = []

        for i, shot in enumerate(screenshots, 1):
            new_name = f"page_{page_num:04d}_{i}.png"
            new_path = shot.parent / new_name

            try:
                # Use replace() instead of rename() to overwrite if exists
                shot.replace(new_path)
                renamed.append(new_path)
                logger.info(f"Renamed to: {new_name}")
            except Exception as e:
                logger.error(f"Failed to rename {shot.name}: {e}")
                renamed.append(shot)

        return renamed

    def cleanup(self):
        """Clean up temporary directory and all screenshots."""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*.png"):
                    file.unlink()
                self.temp_dir.rmdir()
                logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")
