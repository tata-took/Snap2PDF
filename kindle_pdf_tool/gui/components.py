"""Common UI components for Kindle PDF Converter."""

import customtkinter as ctk
from typing import Callable, Optional


class SectionFrame(ctk.CTkFrame):
    """Frame with a section title."""

    def __init__(self, parent, title: str, **kwargs):
        """
        Initialize section frame.

        Args:
            parent: Parent widget
            title: Section title
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)

        # Title label
        self.title_label = ctk.CTkLabel(
            self,
            text=f"━━━ {title} ━━━",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=(10, 15), padx=10, anchor="w")


class LabeledEntry(ctk.CTkFrame):
    """Entry widget with label."""

    def __init__(
        self,
        parent,
        label: str,
        default_value: str = "",
        width: int = 150,
        **kwargs
    ):
        """
        Initialize labeled entry.

        Args:
            parent: Parent widget
            label: Label text
            default_value: Default entry value
            width: Entry width
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Label
        self.label = ctk.CTkLabel(self, text=label, width=150, anchor="w")
        self.label.pack(side="left", padx=(0, 10))

        # Entry
        self.entry = ctk.CTkEntry(self, width=width)
        self.entry.insert(0, default_value)
        self.entry.pack(side="left")

    def get(self) -> str:
        """Get entry value."""
        return self.entry.get()

    def set(self, value: str):
        """Set entry value."""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)


class LabeledSlider(ctk.CTkFrame):
    """Slider widget with label and value display."""

    def __init__(
        self,
        parent,
        label: str,
        from_: float,
        to: float,
        default_value: float,
        command: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize labeled slider.

        Args:
            parent: Parent widget
            label: Label text
            from_: Minimum value
            to: Maximum value
            default_value: Default slider value
            command: Callback function when value changes
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Label
        self.label = ctk.CTkLabel(self, text=label, width=150, anchor="w")
        self.label.pack(side="left", padx=(0, 10))

        # Slider
        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            width=300,
            command=self._on_change
        )
        self.slider.set(default_value)
        self.slider.pack(side="left", padx=(0, 10))

        # Value label
        self.value_label = ctk.CTkLabel(self, text=f"{int(default_value)}", width=50)
        self.value_label.pack(side="left")

        self.callback = command

    def _on_change(self, value):
        """Handle slider value change."""
        int_value = int(value)
        self.value_label.configure(text=str(int_value))
        if self.callback:
            self.callback(int_value)

    def get(self) -> int:
        """Get slider value."""
        return int(self.slider.get())

    def set(self, value: float):
        """Set slider value."""
        self.slider.set(value)


class ProgressFrame(ctk.CTkFrame):
    """Frame for progress display."""

    def __init__(self, parent, **kwargs):
        """
        Initialize progress frame.

        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)

        # Progress bar
        self.progressbar = ctk.CTkProgressBar(self, width=500, height=8)
        self.progressbar.pack(pady=(10, 10), padx=20)
        self.progressbar.set(0)

        # Progress text
        self.progress_label = ctk.CTkLabel(
            self,
            text="0/0 ページ処理中... (0%)",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(pady=5)

        # Remaining time label
        self.time_label = ctk.CTkLabel(
            self,
            text="推定残り時間: --",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.time_label.pack(pady=5)

    def update_progress(
        self,
        current: int,
        total: int,
        remaining_time: Optional[str] = None
    ):
        """
        Update progress display.

        Args:
            current: Current page number
            total: Total page count
            remaining_time: Remaining time string (optional)
        """
        if total > 0:
            progress = current / total
            percentage = int(progress * 100)
        else:
            progress = 0
            percentage = 0

        self.progressbar.set(progress)
        self.progress_label.configure(text=f"{current}/{total} ページ処理中... ({percentage}%)")

        if remaining_time:
            self.time_label.configure(text=f"推定残り時間: {remaining_time}")

    def reset(self):
        """Reset progress display."""
        self.progressbar.set(0)
        self.progress_label.configure(text="0/0 ページ処理中... (0%)")
        self.time_label.configure(text="推定残り時間: --")
