"""Main window for Kindle PDF Converter."""

import os
import time
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, List
import customtkinter as ctk

from .components import SectionFrame, LabeledEntry, LabeledSlider, ProgressFrame
from ..core.capture import ScreenCapture
from ..core.automation import KindleAutomation
from ..core.pdf_generator import PDFGenerator
from ..utils.config import Config, ConfigManager
from ..utils.logger import get_logger


logger = get_logger()


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Window settings
        self.title("Kindle PDF Converter")
        self.geometry("600x900")
        self.resizable(False, False)

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize managers
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()

        # Processing state
        self.is_processing = False
        self.stop_requested = False
        self.start_time = 0

        # Core components
        self.screen_capture: Optional[ScreenCapture] = None
        self.kindle_automation: Optional[KindleAutomation] = None
        self.pdf_generator = PDFGenerator()

        # Build UI
        self.build_ui()

        # Load saved config
        self.load_config_to_ui()

        logger.info("Application started")

    def build_ui(self):
        """Build user interface."""
        # Main container with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self, width=580, height=880)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === Basic Settings ===
        self.basic_section = SectionFrame(self.main_frame, "基本設定")
        self.basic_section.pack(fill="x", padx=10, pady=5)

        self.total_pages_entry = LabeledEntry(
            self.basic_section,
            "総ページ数:",
            str(self.config.total_pages)
        )
        self.total_pages_entry.pack(fill="x", padx=20, pady=5)

        self.start_page_entry = LabeledEntry(
            self.basic_section,
            "開始ページ:",
            str(self.config.start_page)
        )
        self.start_page_entry.pack(fill="x", padx=20, pady=5)

        # === Page Operations ===
        self.page_section = SectionFrame(self.main_frame, "ページ操作")
        self.page_section.pack(fill="x", padx=10, pady=5)

        # Direction
        self.direction_frame = ctk.CTkFrame(self.page_section, fg_color="transparent")
        self.direction_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            self.direction_frame,
            text="読み方向:",
            width=150,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        self.direction_var = ctk.StringVar(value=self.config.direction)
        ctk.CTkRadioButton(
            self.direction_frame,
            text="右開き",
            variable=self.direction_var,
            value="right"
        ).pack(side="left", padx=10)

        ctk.CTkRadioButton(
            self.direction_frame,
            text="左開き",
            variable=self.direction_var,
            value="left"
        ).pack(side="left")

        self.page_wait_entry = LabeledEntry(
            self.page_section,
            "ページめくり待機:",
            str(self.config.page_wait),
            width=80
        )
        self.page_wait_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            self.page_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        self.initial_wait_entry = LabeledEntry(
            self.page_section,
            "初回読み込み待機:",
            str(self.config.initial_wait),
            width=80
        )
        self.initial_wait_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            self.page_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        # === Capture Settings ===
        self.capture_section = SectionFrame(self.main_frame, "キャプチャ設定")
        self.capture_section.pack(fill="x", padx=10, pady=5)

        self.screenshot_count_entry = LabeledEntry(
            self.capture_section,
            "📸 スクショ回数:",
            str(self.config.screenshot_count),
            width=80
        )
        self.screenshot_count_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            self.capture_section,
            text="回",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        self.screenshot_interval_entry = LabeledEntry(
            self.capture_section,
            "スクショ間隔:",
            str(self.config.screenshot_interval),
            width=80
        )
        self.screenshot_interval_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            self.capture_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        # Save mode
        ctk.CTkLabel(
            self.capture_section,
            text="保存方法:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.save_mode_var = ctk.StringVar(value=self.config.save_mode)

        ctk.CTkRadioButton(
            self.capture_section,
            text="最後の1枚のみ",
            variable=self.save_mode_var,
            value="last"
        ).pack(anchor="w", padx=40, pady=2)

        ctk.CTkRadioButton(
            self.capture_section,
            text="すべて保存",
            variable=self.save_mode_var,
            value="all"
        ).pack(anchor="w", padx=40, pady=2)

        ctk.CTkRadioButton(
            self.capture_section,
            text="最良画質を自動選択",
            variable=self.save_mode_var,
            value="best"
        ).pack(anchor="w", padx=40, pady=2)

        # === PDF Settings ===
        self.pdf_section = SectionFrame(self.main_frame, "PDF設定")
        self.pdf_section.pack(fill="x", padx=10, pady=5)

        self.compression_slider = LabeledSlider(
            self.pdf_section,
            "圧縮レベル:",
            from_=1,
            to=5,
            default_value=self.config.compression,
            command=self.on_compression_change
        )
        self.compression_slider.pack(fill="x", padx=20, pady=5)

        # Target size
        self.target_size_var = ctk.BooleanVar(value=self.config.target_size_enabled)
        self.target_size_check = ctk.CTkCheckBox(
            self.pdf_section,
            text="📦 目標ファイルサイズ設定",
            variable=self.target_size_var,
            command=self.on_target_size_toggle
        )
        self.target_size_check.pack(anchor="w", padx=20, pady=5)

        self.target_size_frame = ctk.CTkFrame(self.pdf_section, fg_color="transparent")
        self.target_size_frame.pack(fill="x", padx=40, pady=5)

        self.target_size_entry = LabeledEntry(
            self.target_size_frame,
            "  目標:",
            str(self.config.target_size_mb),
            width=80
        )
        self.target_size_entry.pack(fill="x", pady=2)

        ctk.CTkLabel(
            self.target_size_frame,
            text="MB以下",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(80, 0))

        # Priority
        priority_frame = ctk.CTkFrame(self.target_size_frame, fg_color="transparent")
        priority_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            priority_frame,
            text="  優先度:",
            width=80,
            anchor="w"
        ).pack(side="left")

        self.priority_var = ctk.StringVar(value=self.config.size_priority)

        ctk.CTkRadioButton(
            priority_frame,
            text="画質",
            variable=self.priority_var,
            value="quality"
        ).pack(side="left", padx=5)

        ctk.CTkRadioButton(
            priority_frame,
            text="サイズ",
            variable=self.priority_var,
            value="size"
        ).pack(side="left")

        # Estimated size
        self.estimated_size_label = ctk.CTkLabel(
            self.pdf_section,
            text="💡 推定: -- MB",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.estimated_size_label.pack(anchor="w", padx=20, pady=5)

        # Update initial estimate
        self.update_estimated_size()

        # === Output Settings ===
        self.output_section = SectionFrame(self.main_frame, "出力先")
        self.output_section.pack(fill="x", padx=10, pady=5)

        output_frame = ctk.CTkFrame(self.output_section, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=5)

        default_output = self.config.last_output_path or str(
            Path.home() / "Documents" / "output.pdf"
        )
        self.output_entry = ctk.CTkEntry(output_frame, width=400)
        self.output_entry.insert(0, default_output)
        self.output_entry.pack(side="left", padx=(0, 10))

        self.browse_button = ctk.CTkButton(
            output_frame,
            text="📁 参照",
            width=80,
            command=self.browse_output
        )
        self.browse_button.pack(side="left")

        # === Progress ===
        self.progress_frame = ProgressFrame(self.main_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=10)

        # === Control Buttons ===
        control_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)

        self.start_button = ctk.CTkButton(
            control_frame,
            text="▶ 開始",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_processing
        )
        self.start_button.pack(side="left", padx=(80, 20))

        self.stop_button = ctk.CTkButton(
            control_frame,
            text="⏹ 停止",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.stop_processing,
            state="disabled"
        )
        self.stop_button.pack(side="left")

        # === Status Bar ===
        status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="ステータス: 待機中",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.status_label.pack(side="left")

        self.save_config_button = ctk.CTkButton(
            status_frame,
            text="設定保存",
            width=100,
            height=30,
            command=self.save_config
        )
        self.save_config_button.pack(side="right")

    def load_config_to_ui(self):
        """Load configuration to UI elements."""
        # Already loaded in __init__ via default values
        pass

    def save_config(self):
        """Save current configuration."""
        try:
            config = self.get_config_from_ui()
            if self.config_manager.save(config):
                self.status_label.configure(text="ステータス: 設定を保存しました")
                logger.info("Configuration saved")
            else:
                messagebox.showerror("エラー", "設定の保存に失敗しました")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            messagebox.showerror("エラー", f"設定の保存エラー: {e}")

    def get_config_from_ui(self) -> Config:
        """Get configuration from UI elements."""
        return Config(
            total_pages=int(self.total_pages_entry.get()),
            start_page=int(self.start_page_entry.get()),
            direction=self.direction_var.get(),
            page_wait=float(self.page_wait_entry.get()),
            initial_wait=float(self.initial_wait_entry.get()),
            screenshot_count=int(self.screenshot_count_entry.get()),
            screenshot_interval=float(self.screenshot_interval_entry.get()),
            save_mode=self.save_mode_var.get(),
            compression=self.compression_slider.get(),
            target_size_enabled=self.target_size_var.get(),
            target_size_mb=int(self.target_size_entry.get()),
            size_priority=self.priority_var.get(),
            last_output_path=self.output_entry.get()
        )

    def browse_output(self):
        """Browse for output file location."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile="output.pdf"
        )
        if filename:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, filename)

    def on_compression_change(self, value: int):
        """Handle compression level change."""
        self.update_estimated_size()

    def on_target_size_toggle(self):
        """Handle target size checkbox toggle."""
        enabled = self.target_size_var.get()
        state = "normal" if enabled else "disabled"

        for widget in self.target_size_frame.winfo_children():
            if isinstance(widget, (ctk.CTkEntry, ctk.CTkRadioButton)):
                widget.configure(state=state)
            elif isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, (ctk.CTkEntry, ctk.CTkRadioButton)):
                        child.configure(state=state)

    def update_estimated_size(self):
        """Update estimated file size display."""
        try:
            total_pages = int(self.total_pages_entry.get())
            start_page = int(self.start_page_entry.get())
            compression = self.compression_slider.get()
            save_mode = self.save_mode_var.get()

            page_count = total_pages - start_page + 1
            screenshot_multiplier = 1

            if save_mode == "all":
                screenshot_multiplier = int(self.screenshot_count_entry.get())

            estimated_mb = self.pdf_generator.estimate_file_size(
                page_count,
                compression,
                screenshot_multiplier
            )

            # Update label
            self.estimated_size_label.configure(text=f"💡 推定: {estimated_mb:.1f} MB")

            # Color based on target size
            if self.target_size_var.get():
                target_mb = int(self.target_size_entry.get())
                if estimated_mb <= target_mb:
                    self.estimated_size_label.configure(text_color="green")
                else:
                    self.estimated_size_label.configure(text_color="orange")
            else:
                self.estimated_size_label.configure(text_color="gray")

        except Exception as e:
            logger.error(f"Failed to update estimated size: {e}")

    def validate_inputs(self) -> bool:
        """Validate user inputs."""
        try:
            total_pages = int(self.total_pages_entry.get())
            start_page = int(self.start_page_entry.get())

            if total_pages < 1 or total_pages > 9999:
                messagebox.showerror("エラー", "総ページ数は1-9999の範囲で指定してください")
                return False

            if start_page < 1 or start_page > total_pages:
                messagebox.showerror("エラー", "開始ページは1以上、総ページ数以下で指定してください")
                return False

            page_wait = float(self.page_wait_entry.get())
            if page_wait < 0.5 or page_wait > 10.0:
                messagebox.showerror("エラー", "ページめくり待機は0.5-10.0秒の範囲で指定してください")
                return False

            screenshot_count = int(self.screenshot_count_entry.get())
            if screenshot_count < 1 or screenshot_count > 10:
                messagebox.showerror("エラー", "スクショ回数は1-10回の範囲で指定してください")
                return False

            output_path = self.output_entry.get()
            if not output_path:
                messagebox.showerror("エラー", "出力先を指定してください")
                return False

            return True

        except ValueError as e:
            messagebox.showerror("エラー", f"入力値が不正です: {e}")
            return False

    def start_processing(self):
        """Start PDF generation process."""
        if not self.validate_inputs():
            return

        # Save config before starting
        self.save_config()

        # Start processing in separate thread
        self.is_processing = True
        self.stop_requested = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="ステータス: 処理中...")

        threading.Thread(target=self.processing_thread, daemon=True).start()

    def stop_processing(self):
        """Request to stop processing."""
        self.stop_requested = True
        self.status_label.configure(text="ステータス: 停止中...")
        self.stop_button.configure(state="disabled")

    def processing_thread(self):
        """Main processing thread."""
        try:
            config = self.get_config_from_ui()

            # Initialize components
            temp_dir = Path("./temp_captures")
            self.screen_capture = ScreenCapture(temp_dir)
            self.kindle_automation = KindleAutomation()

            # Find and activate Kindle window
            self.update_status("Kindleウィンドウを検索中...")
            if not self.kindle_automation.initialize():
                self.show_error("Kindleウィンドウが見つかりません。\nKindleアプリを起動して書籍を開いてください。")
                return

            # Initial wait
            self.update_status("初期待機中...")
            time.sleep(config.initial_wait)

            # Process pages
            self.start_time = time.time()
            page_count = config.total_pages - config.start_page + 1
            processed_pages = []

            for i in range(page_count):
                if self.stop_requested:
                    self.update_status("処理を中断しました")
                    break

                current_page = config.start_page + i

                # Capture screenshots
                self.update_status(f"ページ {current_page}: スクリーンショット撮影中...")
                screenshots = self.screen_capture.capture_multiple(
                    current_page,
                    config.screenshot_count,
                    config.screenshot_interval
                )

                # Select screenshots based on mode
                if config.save_mode == "last":
                    final_shot = self.screen_capture.keep_last_screenshot(screenshots)
                    if final_shot:
                        processed_pages.append(final_shot)
                elif config.save_mode == "best":
                    best_shot = self.screen_capture.select_best_screenshot(screenshots)
                    if best_shot:
                        processed_pages.append(best_shot)
                elif config.save_mode == "all":
                    renamed = self.screen_capture.rename_all_screenshots(screenshots, current_page)
                    processed_pages.extend(renamed)

                # Update progress
                self.update_progress(i + 1, page_count)

                # Turn page (except for last page)
                if i < page_count - 1:
                    self.kindle_automation.turn_page(config.direction)
                    time.sleep(config.page_wait)

            if self.stop_requested:
                return

            # Generate PDF
            self.update_status("PDF生成中...")
            output_path = Path(config.last_output_path)

            if config.target_size_enabled and config.size_priority == "size":
                # Optimize for target size
                success, file_size = self.pdf_generator.optimize_for_target_size(
                    processed_pages,
                    output_path,
                    config.target_size_mb
                )
            else:
                # Standard generation
                success, file_size = self.pdf_generator.create_pdf(
                    processed_pages,
                    output_path,
                    config.compression
                )

            if success:
                self.update_status(f"完了！ ({file_size:.2f} MB)")
                messagebox.showinfo(
                    "完了",
                    f"PDFを生成しました！\n\n"
                    f"出力先: {output_path}\n"
                    f"ファイルサイズ: {file_size:.2f} MB"
                )
            else:
                self.show_error("PDF生成に失敗しました")

        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            self.show_error(f"処理エラー: {e}")

        finally:
            # Cleanup
            if self.screen_capture:
                self.screen_capture.cleanup()

            self.after(0, self.reset_ui)

    def update_status(self, message: str):
        """Update status label."""
        def update():
            self.status_label.configure(text=f"ステータス: {message}")

        self.after(0, update)

    def update_progress(self, current: int, total: int):
        """Update progress display."""
        # Calculate remaining time
        elapsed = time.time() - self.start_time
        if current > 0:
            time_per_page = elapsed / current
            remaining_pages = total - current
            remaining_seconds = time_per_page * remaining_pages

            minutes = int(remaining_seconds // 60)
            seconds = int(remaining_seconds % 60)
            time_str = f"{minutes}分{seconds}秒"
        else:
            time_str = None

        def update():
            self.progress_frame.update_progress(current, total, time_str)

        self.after(0, update)

    def show_error(self, message: str):
        """Show error message."""
        def show():
            messagebox.showerror("エラー", message)

        self.after(0, show)

    def reset_ui(self):
        """Reset UI to initial state."""
        self.is_processing = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_frame.reset()
