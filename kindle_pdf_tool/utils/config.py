"""Configuration management for Kindle PDF Converter."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Config:
    """Configuration data class."""

    # Basic settings
    total_pages: int = 200
    start_page: int = 1

    # Page operations
    direction: str = "right"  # "right" or "left"
    page_wait: float = 1.5
    initial_wait: float = 3.0

    # Capture settings
    screenshot_count: int = 1
    screenshot_interval: float = 0.5
    save_mode: str = "last"  # "last", "all", or "best"

    # PDF settings - always maximum quality
    target_size_enabled: bool = True
    target_size_mb: int = 50

    # Output
    last_output_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(self):
        """Initialize ConfigManager."""
        self.config_dir = Path.home() / ".kindle_pdf_tool"
        self.config_file = self.config_dir / "config.json"
        self.config = Config()

    def load(self) -> Config:
        """
        Load configuration from file.

        Returns:
            Config object
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.config = Config.from_dict(data)
            except Exception as e:
                print(f"Failed to load config: {e}")
                self.config = Config()
        else:
            self.config = Config()

        return self.config

    def save(self, config: Optional[Config] = None) -> bool:
        """
        Save configuration to file.

        Args:
            config: Config object to save (uses current if None)

        Returns:
            True if successful, False otherwise
        """
        if config is not None:
            self.config = config

        try:
            # Create directory if not exists
            self.config_dir.mkdir(exist_ok=True)

            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False

    def get_config(self) -> Config:
        """
        Get current configuration.

        Returns:
            Config object
        """
        return self.config
