"""Logging utility for Kindle PDF Converter."""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "kindle_pdf_tool") -> logging.Logger:
    """
    Setup logger with file and console handlers.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create log directory
    log_dir = Path.home() / ".kindle_pdf_tool"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app.log"

    # File handler with rotation (10MB max)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "kindle_pdf_tool") -> logging.Logger:
    """
    Get existing logger or create new one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
