"""Main window for Kindle PDF Converter - Compact UI version."""

import os
import time
import threading
import subprocess
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, List
import customtkinter as ctk

from .components import LabeledEntry, LabeledSlider, ProgressFrame
from ..core.capture import ScreenCapture
from ..core.automation import KindleAutomation
from ..core.pdf_generator import PDFGenerator
from ..utils.config import Config, ConfigManager
from ..utils.logger import get_logger


logger = get_logger()

# Readable Japanese font
JP_FONT = ("Yu Gothic UI", 11)
JP_FONT_BOLD = ("Yu Gothic UI", 12, "bold")
JP_FONT_SMALL = ("Yu Gothic UI", 10)


class CompactSection(ctk.CTkFrame):
    """Compact section frame."""

    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.title_label = ctk.CTkLabel(
            self,
            text=f"━ {title} ━",
            font=JP_FONT_BOLD
        )
        self.title_label.pack(pady=(5, 5), padx=10, anchor="w")


class MainWindow(ctk.CTk):
    """Main application window with compact tabbed interface."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Window settings
        self.title("Kindle PDF Converter v1.1")
        self.geometry("680x750")
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
        self.screenshot_output_dir: Optional[Path] = None

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
        """Build user interface with tabs."""
        # Main container
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Tab view
        self.tabview = ctk.CTkTabview(main_container, width=664, height=734)
        self.tabview.pack(fill="both", expand=True)

        # Add tabs
        self.tabview.add("📸 撮影")
        self.tabview.add("📄 変換")

        # Build screenshot tab
        self.build_screenshot_tab()

        # Build PDF conversion tab
        self.build_pdf_tab()

    def build_screenshot_tab(self):
        """Build screenshot capture tab."""
        tab = self.tabview.tab("📸 撮影")

        # Main frame (no scroll)
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # === Basic Settings ===
        basic_section = CompactSection(main_frame, "基本設定")
        basic_section.pack(fill="x", padx=5, pady=3)

        row1 = ctk.CTkFrame(basic_section, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row1, text="総ページ数:", width=90, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.total_pages_entry = ctk.CTkEntry(row1, width=70)
        self.total_pages_entry.insert(0, str(self.config.total_pages))
        self.total_pages_entry.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row1, text="開始ページ:", width=80, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.start_page_entry = ctk.CTkEntry(row1, width=70)
        self.start_page_entry.insert(0, str(self.config.start_page))
        self.start_page_entry.pack(side="left")

        # === Page Operations ===
        page_section = CompactSection(main_frame, "ページ操作")
        page_section.pack(fill="x", padx=5, pady=3)

        row2 = ctk.CTkFrame(page_section, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row2, text="読み方向:", width=70, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.direction_var = ctk.StringVar(value=self.config.direction)
        ctk.CTkRadioButton(row2, text="右開き", variable=self.direction_var, value="right", font=JP_FONT).pack(side="left", padx=5)
        ctk.CTkRadioButton(row2, text="左開き", variable=self.direction_var, value="left", font=JP_FONT).pack(side="left", padx=5)

        row3 = ctk.CTkFrame(page_section, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row3, text="ページ待機:", width=90, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.page_wait_entry = ctk.CTkEntry(row3, width=60)
        self.page_wait_entry.insert(0, str(self.config.page_wait))
        self.page_wait_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(row3, text="秒", font=JP_FONT_SMALL).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row3, text="初回待機:", width=70, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.initial_wait_entry = ctk.CTkEntry(row3, width=60)
        self.initial_wait_entry.insert(0, str(self.config.initial_wait))
        self.initial_wait_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(row3, text="秒", font=JP_FONT_SMALL).pack(side="left")

        # === Capture Settings ===
        capture_section = CompactSection(main_frame, "撮影設定")
        capture_section.pack(fill="x", padx=5, pady=3)

        row4 = ctk.CTkFrame(capture_section, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row4, text="回数/ページ:", width=90, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.screenshot_count_entry = ctk.CTkEntry(row4, width=60)
        self.screenshot_count_entry.insert(0, str(self.config.screenshot_count))
        self.screenshot_count_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(row4, text="回", font=JP_FONT_SMALL).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row4, text="間隔:", width=50, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))
        self.screenshot_interval_entry = ctk.CTkEntry(row4, width=60)
        self.screenshot_interval_entry.insert(0, str(self.config.screenshot_interval))
        self.screenshot_interval_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(row4, text="秒", font=JP_FONT_SMALL).pack(side="left")

        # === Output Directory ===
        output_section = CompactSection(main_frame, "保存先")
        output_section.pack(fill="x", padx=5, pady=3)

        row5 = ctk.CTkFrame(output_section, fg_color="transparent")
        row5.pack(fill="x", padx=10, pady=2)

        default_screenshot_dir = str(Path.home() / "Documents" / "kindle_screenshots")
        self.screenshot_dir_entry = ctk.CTkEntry(row5, width=480, font=JP_FONT)
        self.screenshot_dir_entry.insert(0, default_screenshot_dir)
        self.screenshot_dir_entry.pack(side="left", padx=(0, 5))

        browse_dir_btn = ctk.CTkButton(row5, text="参照", width=60, command=self.browse_screenshot_dir, font=JP_FONT)
        browse_dir_btn.pack(side="left")

        # === Progress ===
        self.screenshot_progress = ProgressFrame(main_frame)
        self.screenshot_progress.pack(fill="x", padx=5, pady=5)

        # === Control Buttons ===
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=10, pady=5)

        self.screenshot_start_btn = ctk.CTkButton(
            control_frame,
            text="▶ 撮影開始",
            width=140,
            height=36,
            font=JP_FONT_BOLD,
            command=self.start_screenshot
        )
        self.screenshot_start_btn.pack(side="left", padx=(100, 10))

        self.screenshot_stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹ 停止",
            width=100,
            height=36,
            font=JP_FONT_BOLD,
            command=self.stop_processing,
            state="disabled"
        )
        self.screenshot_stop_btn.pack(side="left")

        # === Status ===
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=3)

        self.screenshot_status = ctk.CTkLabel(
            status_frame,
            text="ステータス: 待機中",
            font=JP_FONT_SMALL,
            anchor="w"
        )
        self.screenshot_status.pack(side="left")

        save_config_btn = ctk.CTkButton(
            status_frame,
            text="設定保存",
            width=80,
            height=26,
            command=self.save_config,
            font=JP_FONT
        )
        save_config_btn.pack(side="right")

    def build_pdf_tab(self):
        """Build PDF conversion tab."""
        tab = self.tabview.tab("📄 変換")

        # Main frame (no scroll)
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # === Image Source ===
        source_section = CompactSection(main_frame, "画像フォルダ")
        source_section.pack(fill="x", padx=5, pady=3)

        row1 = ctk.CTkFrame(source_section, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        self.image_folder_entry = ctk.CTkEntry(row1, width=440, font=JP_FONT)
        self.image_folder_entry.insert(0, "画像フォルダを選択")
        self.image_folder_entry.pack(side="left", padx=(0, 5))

        browse_folder_btn = ctk.CTkButton(row1, text="選択", width=60, command=self.browse_image_folder, font=JP_FONT)
        browse_folder_btn.pack(side="left", padx=(0, 5))

        self.open_folder_btn = ctk.CTkButton(
            row1,
            text="開く",
            width=60,
            command=self.open_image_folder,
            state="disabled",
            font=JP_FONT
        )
        self.open_folder_btn.pack(side="left")

        row2 = ctk.CTkFrame(source_section, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=2)

        self.image_count_label = ctk.CTkLabel(row2, text="画像数: 未選択", font=JP_FONT, text_color="gray")
        self.image_count_label.pack(side="left")

        # === PDF Settings ===
        pdf_section = CompactSection(main_frame, "PDF設定")
        pdf_section.pack(fill="x", padx=5, pady=3)

        row3 = ctk.CTkFrame(pdf_section, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row3, text="圧縮:", width=50, anchor="w", font=JP_FONT).pack(side="left", padx=(0, 5))

        self.compression_slider = ctk.CTkSlider(
            row3,
            from_=1,
            to=5,
            width=250,
            command=self._on_compression_change
        )
        self.compression_slider.set(self.config.compression)
        self.compression_slider.pack(side="left", padx=(0, 8))

        self.compression_label = ctk.CTkLabel(row3, text=f"{self.config.compression}", width=30, font=JP_FONT)
        self.compression_label.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(row3, text="(1:高画質 5:小容量)", font=JP_FONT_SMALL, text_color="gray").pack(side="left")

        # Target size
        row4 = ctk.CTkFrame(pdf_section, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=2)

        self.target_size_var = ctk.BooleanVar(value=self.config.target_size_enabled)
        target_size_check = ctk.CTkCheckBox(
            row4,
            text="目標サイズ:",
            variable=self.target_size_var,
            command=self.on_target_size_toggle,
            font=JP_FONT
        )
        target_size_check.pack(side="left", padx=(0, 5))

        self.target_size_entry = ctk.CTkEntry(row4, width=60)
        self.target_size_entry.insert(0, str(self.config.target_size_mb))
        self.target_size_entry.pack(side="left", padx=(0, 3))

        ctk.CTkLabel(row4, text="MB", font=JP_FONT).pack(side="left", padx=(0, 10))

        self.priority_var = ctk.StringVar(value=self.config.size_priority)
        ctk.CTkRadioButton(row4, text="画質優先", variable=self.priority_var, value="quality", font=JP_FONT).pack(side="left", padx=5)
        ctk.CTkRadioButton(row4, text="サイズ優先", variable=self.priority_var, value="size", font=JP_FONT).pack(side="left")

        row5 = ctk.CTkFrame(pdf_section, fg_color="transparent")
        row5.pack(fill="x", padx=10, pady=2)

        self.pdf_estimated_size_label = ctk.CTkLabel(row5, text="💡 推定: -- MB", font=JP_FONT, text_color="gray")
        self.pdf_estimated_size_label.pack(side="left")

        # === Output ===
        output_section = CompactSection(main_frame, "出力先")
        output_section.pack(fill="x", padx=5, pady=3)

        row6 = ctk.CTkFrame(output_section, fg_color="transparent")
        row6.pack(fill="x", padx=10, pady=2)

        default_output = self.config.last_output_path or str(Path.home() / "Documents" / "output.pdf")
        self.pdf_output_entry = ctk.CTkEntry(row6, width=480, font=JP_FONT)
        self.pdf_output_entry.insert(0, default_output)
        self.pdf_output_entry.pack(side="left", padx=(0, 5))

        browse_output_btn = ctk.CTkButton(row6, text="参照", width=60, command=self.browse_pdf_output, font=JP_FONT)
        browse_output_btn.pack(side="left")

        # === Progress ===
        self.pdf_progress = ProgressFrame(main_frame)
        self.pdf_progress.pack(fill="x", padx=5, pady=5)

        # === Control Buttons ===
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=10, pady=5)

        self.pdf_convert_btn = ctk.CTkButton(
            control_frame,
            text="📄 PDF生成",
            width=140,
            height=36,
            font=JP_FONT_BOLD,
            command=self.start_pdf_conversion
        )
        self.pdf_convert_btn.pack(side="left", padx=(160, 10))

        # === Status ===
        self.pdf_status = ctk.CTkLabel(
            main_frame,
            text="ステータス: 待機中",
            font=JP_FONT_SMALL,
            anchor="w"
        )
        self.pdf_status.pack(anchor="w", padx=10, pady=3)

    def _on_compression_change(self, value):
        """Handle compression slider change."""
        int_value = int(value)
        self.compression_label.configure(text=str(int_value))
        self.on_compression_change(int_value)

    def load_config_to_ui(self):
        """Load configuration to UI elements."""
        pass

    def save_config(self):
        """Save current configuration."""
        try:
            config = self.get_config_from_ui()
            if self.config_manager.save(config):
                self.screenshot_status.configure(text="ステータス: 設定を保存しました")
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
            save_mode="all",
            compression=int(self.compression_slider.get()),
            target_size_enabled=self.target_size_var.get(),
            target_size_mb=int(self.target_size_entry.get()),
            size_priority=self.priority_var.get(),
            last_output_path=self.pdf_output_entry.get()
        )

    def browse_screenshot_dir(self):
        """Browse for screenshot output directory."""
        directory = filedialog.askdirectory(title="保存先を選択")
        if directory:
            self.screenshot_dir_entry.delete(0, "end")
            self.screenshot_dir_entry.insert(0, directory)

    def browse_image_folder(self):
        """Browse for image folder."""
        directory = filedialog.askdirectory(title="画像フォルダを選択")
        if directory:
            self.image_folder_entry.delete(0, "end")
            self.image_folder_entry.insert(0, directory)
            self.update_image_count(Path(directory))
            self.open_folder_btn.configure(state="normal")

    def browse_pdf_output(self):
        """Browse for PDF output file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile="output.pdf"
        )
        if filename:
            self.pdf_output_entry.delete(0, "end")
            self.pdf_output_entry.insert(0, filename)

    def update_image_count(self, folder: Path):
        """Update image count display."""
        try:
            image_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
            count = len(image_files)
            self.image_count_label.configure(
                text=f"画像数: {count}枚",
                text_color="green" if count > 0 else "orange"
            )

            if count > 0:
                compression = int(self.compression_slider.get())
                estimated_mb = self.pdf_generator.estimate_file_size(count, compression, 1)
                self.pdf_estimated_size_label.configure(text=f"💡 推定: {estimated_mb:.1f} MB")
        except Exception as e:
            logger.error(f"Failed to count images: {e}")
            self.image_count_label.configure(text="画像数: エラー", text_color="red")

    def open_image_folder(self):
        """Open image folder in file explorer."""
        folder_path = self.image_folder_entry.get()
        if folder_path and Path(folder_path).exists():
            try:
                if os.name == 'nt':
                    os.startfile(folder_path)
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', folder_path])
            except Exception as e:
                logger.error(f"Failed to open folder: {e}")
                messagebox.showerror("エラー", f"フォルダを開けません: {e}")

    def on_compression_change(self, value: int):
        """Handle compression level change."""
        folder_path = self.image_folder_entry.get()
        if folder_path and Path(folder_path).exists():
            self.update_image_count(Path(folder_path))

    def on_target_size_toggle(self):
        """Handle target size checkbox toggle."""
        enabled = self.target_size_var.get()
        state = "normal" if enabled else "disabled"
        self.target_size_entry.configure(state=state)

    def validate_screenshot_inputs(self) -> bool:
        """Validate screenshot mode inputs."""
        try:
            total_pages = int(self.total_pages_entry.get())
            start_page = int(self.start_page_entry.get())

            if total_pages < 1 or total_pages > 9999:
                messagebox.showerror("エラー", "総ページ数は1-9999で指定")
                return False

            if start_page < 1 or start_page > total_pages:
                messagebox.showerror("エラー", "開始ページが不正です")
                return False

            page_wait = float(self.page_wait_entry.get())
            if page_wait < 0.1 or page_wait > 10.0:
                messagebox.showerror("エラー", "待機時間は0.1-10.0秒")
                return False

            screenshot_count = int(self.screenshot_count_entry.get())
            if screenshot_count < 1 or screenshot_count > 10:
                messagebox.showerror("エラー", "撮影回数は1-10回")
                return False

            output_dir = self.screenshot_dir_entry.get()
            if not output_dir:
                messagebox.showerror("エラー", "保存先を指定してください")
                return False

            return True

        except ValueError:
            messagebox.showerror("エラー", "入力値が不正です")
            return False

    def validate_pdf_inputs(self) -> bool:
        """Validate PDF mode inputs."""
        folder_path = self.image_folder_entry.get()
        if not folder_path or not Path(folder_path).exists():
            messagebox.showerror("エラー", "画像フォルダを選択してください")
            return False

        output_path = self.pdf_output_entry.get()
        if not output_path:
            messagebox.showerror("エラー", "出力先を指定してください")
            return False

        return True

    def start_screenshot(self):
        """Start screenshot capture."""
        if not self.validate_screenshot_inputs():
            return

        self.save_config()

        self.is_processing = True
        self.stop_requested = False
        self.screenshot_start_btn.configure(state="disabled")
        self.screenshot_stop_btn.configure(state="normal")
        self.screenshot_status.configure(text="ステータス: 処理中...")

        threading.Thread(target=self.screenshot_thread, daemon=True).start()

    def start_pdf_conversion(self):
        """Start PDF conversion."""
        if not self.validate_pdf_inputs():
            return

        self.is_processing = True
        self.pdf_convert_btn.configure(state="disabled")
        self.pdf_status.configure(text="ステータス: PDF生成中...")

        threading.Thread(target=self.pdf_conversion_thread, daemon=True).start()

    def stop_processing(self):
        """Request to stop processing."""
        self.stop_requested = True
        self.screenshot_status.configure(text="ステータス: 停止中...")
        self.screenshot_stop_btn.configure(state="disabled")

    def screenshot_thread(self):
        """Screenshot capture thread."""
        try:
            config = self.get_config_from_ui()

            output_dir = Path(self.screenshot_dir_entry.get())
            output_dir.mkdir(parents=True, exist_ok=True)

            self.screen_capture = ScreenCapture(output_dir)
            self.kindle_automation = KindleAutomation()

            self.update_screenshot_status("Kindle検索中...")
            if not self.kindle_automation.initialize():
                self.show_error("Kindleが見つかりません\nKindleアプリを起動してください")
                return

            self.update_screenshot_status("待機中...")
            time.sleep(config.initial_wait)

            self.start_time = time.time()
            page_count = config.total_pages - config.start_page + 1

            for i in range(page_count):
                if self.stop_requested:
                    self.update_screenshot_status("中断しました")
                    break

                current_page = config.start_page + i

                self.update_screenshot_status(f"ページ {current_page} 撮影中...")
                screenshots = self.screen_capture.capture_multiple(
                    current_page,
                    config.screenshot_count,
                    config.screenshot_interval
                )

                self.screen_capture.rename_all_screenshots(screenshots, current_page)

                self.update_screenshot_progress(i + 1, page_count)

                if i < page_count - 1:
                    self.kindle_automation.turn_page(config.direction)
                    time.sleep(config.page_wait)

            if not self.stop_requested:
                self.update_screenshot_status("完了！")
                self.show_info(
                    "撮影完了",
                    f"保存先: {output_dir}\n"
                    f"撮影枚数: {page_count * config.screenshot_count}枚\n\n"
                    f"画像を確認後、PDF変換タブへ"
                )

                self.after(0, lambda: self.switch_to_pdf_tab(output_dir))

        except Exception as e:
            logger.error(f"Screenshot error: {e}", exc_info=True)
            self.show_error(f"エラー: {e}")

        finally:
            self.after(0, self.reset_screenshot_ui)

    def pdf_conversion_thread(self):
        """PDF conversion thread."""
        try:
            folder_path = Path(self.image_folder_entry.get())

            image_files = sorted(
                list(folder_path.glob("*.jpg")) +
                list(folder_path.glob("*.jpeg")) +
                list(folder_path.glob("*.png"))
            )

            if not image_files:
                self.show_error("画像ファイルが見つかりません")
                return

            self.update_pdf_status(f"PDF生成中... ({len(image_files)}枚)")

            config = self.get_config_from_ui()
            output_path = Path(self.pdf_output_entry.get())
            compression = int(self.compression_slider.get())

            if config.target_size_enabled and config.size_priority == "size":
                success, file_size = self.pdf_generator.optimize_for_target_size(
                    image_files,
                    output_path,
                    config.target_size_mb
                )
            else:
                success, file_size = self.pdf_generator.create_pdf(
                    image_files,
                    output_path,
                    compression
                )

            if success:
                self.update_pdf_status(f"完了！ ({file_size:.2f} MB)")
                self.show_info(
                    "PDF生成完了",
                    f"出力先: {output_path}\n"
                    f"サイズ: {file_size:.2f} MB\n"
                    f"ページ数: {len(image_files)}"
                )
            else:
                self.show_error("PDF生成に失敗しました")

        except Exception as e:
            logger.error(f"PDF conversion error: {e}", exc_info=True)
            self.show_error(f"エラー: {e}")

        finally:
            self.after(0, self.reset_pdf_ui)

    def switch_to_pdf_tab(self, folder_path: Path):
        """Switch to PDF tab and set folder."""
        self.tabview.set("📄 変換")
        self.image_folder_entry.delete(0, "end")
        self.image_folder_entry.insert(0, str(folder_path))
        self.update_image_count(folder_path)
        self.open_folder_btn.configure(state="normal")

    def update_screenshot_status(self, message: str):
        """Update screenshot status label."""
        def update():
            self.screenshot_status.configure(text=f"ステータス: {message}")
        self.after(0, update)

    def update_pdf_status(self, message: str):
        """Update PDF status label."""
        def update():
            self.pdf_status.configure(text=f"ステータス: {message}")
        self.after(0, update)

    def update_screenshot_progress(self, current: int, total: int):
        """Update screenshot progress display."""
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
            self.screenshot_progress.update_progress(current, total, time_str)
        self.after(0, update)

    def show_error(self, message: str):
        """Show error message."""
        def show():
            messagebox.showerror("エラー", message)
        self.after(0, show)

    def show_info(self, title: str, message: str):
        """Show info message."""
        def show():
            messagebox.showinfo(title, message)
        self.after(0, show)

    def reset_screenshot_ui(self):
        """Reset screenshot UI to initial state."""
        self.is_processing = False
        self.screenshot_start_btn.configure(state="normal")
        self.screenshot_stop_btn.configure(state="disabled")
        self.screenshot_progress.reset()

    def reset_pdf_ui(self):
        """Reset PDF UI to initial state."""
        self.is_processing = False
        self.pdf_convert_btn.configure(state="normal")
        self.pdf_progress.reset()
