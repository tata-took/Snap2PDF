#!/usr/bin/env python3
"""
Kindle PDF Converter

Convert Kindle books to PDF by automatically capturing screenshots.
For personal use only.
"""

import sys
from kindle_pdf_tool.gui.main_window import MainWindow
from kindle_pdf_tool.utils.logger import setup_logger


def main():
    """Main entry point."""
    # Setup logger
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("Kindle PDF Converter Starting")
    logger.info("=" * 60)

    try:
        # Create and run application
        app = MainWindow()
        app.mainloop()

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("Application closed")


if __name__ == "__main__":
    main()
