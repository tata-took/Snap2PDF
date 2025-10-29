"""Main window for Kindle PDF Converter with separate Screenshot and PDF modes."""

import os
import time
import threading
import subprocess
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
    """Main application window with tabbed interface."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Window settings
        self.title("Kindle PDF Converter")
        self.geometry("700x850")
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
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab view
        self.tabview = ctk.CTkTabview(main_container, width=680, height=800)
        self.tabview.pack(fill="both", expand=True)

        # Add tabs
        self.tabview.add("📸 スクショ撮影")
        self.tabview.add("📄 PDF変換")

        # Build screenshot tab
        self.build_screenshot_tab()

        # Build PDF conversion tab
        self.build_pdf_tab()

    def build_screenshot_tab(self):
        """Build screenshot capture tab."""
        tab = self.tabview.tab("📸 スクショ撮影")

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(tab, width=650, height=700)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Info label
        info_label = ctk.CTkLabel(
            scroll_frame,
            text="Kindleアプリから自動的にスクリーンショットを撮影します。\n撮影後、画像を手動で確認・選定してからPDF変換できます。",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=600
        )
        info_label.pack(pady=(5, 15))

        # === Basic Settings ===
        basic_section = SectionFrame(scroll_frame, "基本設定")
        basic_section.pack(fill="x", padx=10, pady=5)

        self.total_pages_entry = LabeledEntry(
            basic_section,
            "総ページ数:",
            str(self.config.total_pages)
        )
        self.total_pages_entry.pack(fill="x", padx=20, pady=5)

        self.start_page_entry = LabeledEntry(
            basic_section,
            "開始ページ:",
            str(self.config.start_page)
        )
        self.start_page_entry.pack(fill="x", padx=20, pady=5)

        # === Page Operations ===
        page_section = SectionFrame(scroll_frame, "ページ操作")
        page_section.pack(fill="x", padx=10, pady=5)

        # Direction
        direction_frame = ctk.CTkFrame(page_section, fg_color="transparent")
        direction_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            direction_frame,
            text="読み方向:",
            width=150,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        self.direction_var = ctk.StringVar(value=self.config.direction)
        ctk.CTkRadioButton(
            direction_frame,
            text="右開き",
            variable=self.direction_var,
            value="right"
        ).pack(side="left", padx=10)

        ctk.CTkRadioButton(
            direction_frame,
            text="左開き",
            variable=self.direction_var,
            value="left"
        ).pack(side="left")

        self.page_wait_entry = LabeledEntry(
            page_section,
            "ページめくり待機:",
            str(self.config.page_wait),
            width=80
        )
        self.page_wait_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            page_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        self.initial_wait_entry = LabeledEntry(
            page_section,
            "初回読み込み待機:",
            str(self.config.initial_wait),
            width=80
        )
        self.initial_wait_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            page_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        # === Capture Settings ===
        capture_section = SectionFrame(scroll_frame, "キャプチャ設定")
        capture_section.pack(fill="x", padx=10, pady=5)

        self.screenshot_count_entry = LabeledEntry(
            capture_section,
            "📸 スクショ回数/ページ:",
            str(self.config.screenshot_count),
            width=80
        )
        self.screenshot_count_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            capture_section,
            text="回（撮影後、最良のものを手動で選べます）",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(anchor="w", padx=(180, 0))

        self.screenshot_interval_entry = LabeledEntry(
            capture_section,
            "スクショ間隔:",
            str(self.config.screenshot_interval),
            width=80
        )
        self.screenshot_interval_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            capture_section,
            text="秒",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=(180, 0))

        # === Output Directory ===
        output_section = SectionFrame(scroll_frame, "保存先")
        output_section.pack(fill="x", padx=10, pady=5)

        output_frame = ctk.CTkFrame(output_section, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=5)

        default_screenshot_dir = str(Path.home() / "Documents" / "kindle_screenshots")
        self.screenshot_dir_entry = ctk.CTkEntry(output_frame, width=450)
        self.screenshot_dir_entry.insert(0, default_screenshot_dir)
        self.screenshot_dir_entry.pack(side="left", padx=(0, 10))

        browse_dir_btn = ctk.CTkButton(
            output_frame,
            text="📁 参照",
            width=80,
            command=self.browse_screenshot_dir
        )
        browse_dir_btn.pack(side="left")

        ctk.CTkLabel(
            output_section,
            text="💡 撮影した画像は上記フォルダに保存されます",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # === Progress ===
        self.screenshot_progress = ProgressFrame(scroll_frame)
        self.screenshot_progress.pack(fill="x", padx=10, pady=10)

        # === Control Buttons ===
        control_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)

        self.screenshot_start_btn = ctk.CTkButton(
            control_frame,
            text="▶ スクショ開始",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_screenshot
        )
        self.screenshot_start_btn.pack(side="left", padx=(100, 20))

        self.screenshot_stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹ 停止",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.stop_processing,
            state="disabled"
        )
        self.screenshot_stop_btn.pack(side="left")

        # === Status ===
        status_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=10)

        self.screenshot_status = ctk.CTkLabel(
            status_frame,
            text="ステータス: 待機中",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.screenshot_status.pack(side="left")

        save_config_btn = ctk.CTkButton(
            status_frame,
            text="設定保存",
            width=100,
            height=30,
            command=self.save_config
        )
        save_config_btn.pack(side="right")

    def build_pdf_tab(self):
        """Build PDF conversion tab."""
        tab = self.tabview.tab("📄 PDF変換")

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(tab, width=650, height=700)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Info label
        info_label = ctk.CTkLabel(
            scroll_frame,
            text="撮影済みの画像フォルダを選択してPDFに変換します。\n事前に不要な画像を削除しておくことをおすすめします。",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=600
        )
        info_label.pack(pady=(5, 15))

        # === Image Source ===
        source_section = SectionFrame(scroll_frame, "画像フォルダ選択")
        source_section.pack(fill="x", padx=10, pady=5)

        source_frame = ctk.CTkFrame(source_section, fg_color="transparent")
        source_frame.pack(fill="x", padx=20, pady=5)

        self.image_folder_entry = ctk.CTkEntry(source_frame, width=450)
        self.image_folder_entry.insert(0, "画像フォルダを選択してください")
        self.image_folder_entry.pack(side="left", padx=(0, 10))

        browse_folder_btn = ctk.CTkButton(
            source_frame,
            text="📁 フォルダ選択",
            width=120,
            command=self.browse_image_folder
        )
        browse_folder_btn.pack(side="left")

        # Image count display
        self.image_count_label = ctk.CTkLabel(
            source_section,
            text="画像数: 未選択",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.image_count_label.pack(anchor="w", padx=20, pady=5)

        # Open folder button
        self.open_folder_btn = ctk.CTkButton(
            source_section,
            text="🖼️ フォルダを開く",
            width=150,
            command=self.open_image_folder,
            state="disabled"
        )
        self.open_folder_btn.pack(anchor="w", padx=20, pady=5)

        # === PDF Settings ===
        pdf_section = SectionFrame(scroll_frame, "PDF設定")
        pdf_section.pack(fill="x", padx=10, pady=5)

        self.compression_slider = LabeledSlider(
            pdf_section,
            "圧縮レベル:",
            from_=1,
            to=5,
            default_value=self.config.compression,
            command=self.on_compression_change
        )
        self.compression_slider.pack(fill="x", padx=20, pady=5)

        compression_info = ctk.CTkLabel(
            pdf_section,
            text="1:高画質・大容量 → 5:低画質・小容量",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        compression_info.pack(anchor="w", padx=20, pady=(0, 10))

        # Target size
        self.target_size_var = ctk.BooleanVar(value=self.config.target_size_enabled)
        target_size_check = ctk.CTkCheckBox(
            pdf_section,
            text="📦 目標ファイルサイズ設定",
            variable=self.target_size_var,
            command=self.on_target_size_toggle
        )
        target_size_check.pack(anchor="w", padx=20, pady=5)

        self.target_size_frame = ctk.CTkFrame(pdf_section, fg_color="transparent")
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
        self.pdf_estimated_size_label = ctk.CTkLabel(
            pdf_section,
            text="💡 推定: -- MB",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.pdf_estimated_size_label.pack(anchor="w", padx=20, pady=5)

        # === Output ===
        output_section = SectionFrame(scroll_frame, "出力先")
        output_section.pack(fill="x", padx=10, pady=5)

        output_frame = ctk.CTkFrame(output_section, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=5)

        default_output = self.config.last_output_path or str(
            Path.home() / "Documents" / "output.pdf"
        )
        self.pdf_output_entry = ctk.CTkEntry(output_frame, width=450)
        self.pdf_output_entry.insert(0, default_output)
        self.pdf_output_entry.pack(side="left", padx=(0, 10))

        browse_output_btn = ctk.CTkButton(
            output_frame,
            text="📁 参照",
            width=80,
            command=self.browse_pdf_output
        )
        browse_output_btn.pack(side="left")

        # === Progress ===
        self.pdf_progress = ProgressFrame(scroll_frame)
        self.pdf_progress.pack(fill="x", padx=10, pady=10)

        # === Control Buttons ===
        control_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)

        self.pdf_convert_btn = ctk.CTkButton(
            control_frame,
            text="📄 PDF生成",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_pdf_conversion
        )
        self.pdf_convert_btn.pack(side="left", padx=(150, 20))

        # === Status ===
        self.pdf_status = ctk.CTkLabel(
            scroll_frame,
            text="ステータス: 待機中",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.pdf_status.pack(anchor="w", padx=20, pady=10)

    def load_config_to_ui(self):
        """Load configuration to UI elements."""
        # Already loaded via default values
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
            save_mode="all",  # Always save all in screenshot mode
            compression=self.compression_slider.get(),
            target_size_enabled=self.target_size_var.get(),
            target_size_mb=int(self.target_size_entry.get()),
            size_priority=self.priority_var.get(),
            last_output_path=self.pdf_output_entry.get()
        )

    def browse_screenshot_dir(self):
        """Browse for screenshot output directory."""
        directory = filedialog.askdirectory(
            title="スクリーンショット保存先を選択"
        )
        if directory:
            self.screenshot_dir_entry.delete(0, "end")
            self.screenshot_dir_entry.insert(0, directory)

    def browse_image_folder(self):
        """Browse for image folder."""
        directory = filedialog.askdirectory(
            title="画像フォルダを選択"
        )
        if directory:
            self.image_folder_entry.delete(0, "end")
            self.image_folder_entry.insert(0, directory)

            # Count images
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

            # Update PDF size estimate
            if count > 0:
                compression = self.compression_slider.get()
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
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.Popen(['xdg-open', folder_path])
            except Exception as e:
                logger.error(f"Failed to open folder: {e}")
                messagebox.showerror("エラー", f"フォルダを開けません: {e}")

    def on_compression_change(self, value: int):
        """Handle compression level change."""
        # Update estimate if folder is selected
        folder_path = self.image_folder_entry.get()
        if folder_path and Path(folder_path).exists():
            self.update_image_count(Path(folder_path))

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

    def validate_screenshot_inputs(self) -> bool:
        """Validate screenshot mode inputs."""
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

            output_dir = self.screenshot_dir_entry.get()
            if not output_dir:
                messagebox.showerror("エラー", "保存先を指定してください")
                return False

            return True

        except ValueError as e:
            messagebox.showerror("エラー", f"入力値が不正です: {e}")
            return False

    def validate_pdf_inputs(self) -> bool:
        """Validate PDF mode inputs."""
        folder_path = self.image_folder_entry.get()
        if not folder_path or not Path(folder_path).exists():
            messagebox.showerror("エラー", "有効な画像フォルダを選択してください")
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

            # Create output directory
            output_dir = Path(self.screenshot_dir_entry.get())
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize components
            self.screen_capture = ScreenCapture(output_dir)
            self.kindle_automation = KindleAutomation()

            # Find and activate Kindle window
            self.update_screenshot_status("Kindleウィンドウを検索中...")
            if not self.kindle_automation.initialize():
                self.show_error("Kindleウィンドウが見つかりません。\nKindleアプリを起動して書籍を開いてください。")
                return

            # Initial wait
            self.update_screenshot_status("初期待機中...")
            time.sleep(config.initial_wait)

            # Process pages
            self.start_time = time.time()
            page_count = config.total_pages - config.start_page + 1

            for i in range(page_count):
                if self.stop_requested:
                    self.update_screenshot_status("処理を中断しました")
                    break

                current_page = config.start_page + i

                # Capture multiple screenshots
                self.update_screenshot_status(f"ページ {current_page}: スクリーンショット撮影中...")
                screenshots = self.screen_capture.capture_multiple(
                    current_page,
                    config.screenshot_count,
                    config.screenshot_interval
                )

                # Keep all screenshots with proper naming
                self.screen_capture.rename_all_screenshots(screenshots, current_page)

                # Update progress
                self.update_screenshot_progress(i + 1, page_count)

                # Turn page (except for last page)
                if i < page_count - 1:
                    self.kindle_automation.turn_page(config.direction)
                    time.sleep(config.page_wait)

            if not self.stop_requested:
                self.update_screenshot_status("完了！")
                self.show_info(
                    "スクリーンショット撮影完了",
                    f"画像を保存しました！\n\n"
                    f"保存先: {output_dir}\n"
                    f"撮影枚数: {page_count * config.screenshot_count}枚\n\n"
                    f"フォルダを開いて不要な画像を削除してから、\n"
                    f"「PDF変換」タブでPDFに変換してください。"
                )

                # Switch to PDF tab and set the folder
                self.after(0, lambda: self.switch_to_pdf_tab(output_dir))

        except Exception as e:
            logger.error(f"Screenshot error: {e}", exc_info=True)
            self.show_error(f"処理エラー: {e}")

        finally:
            # Don't cleanup - keep the files
            self.after(0, self.reset_screenshot_ui)

    def pdf_conversion_thread(self):
        """PDF conversion thread."""
        try:
            # Get image folder
            folder_path = Path(self.image_folder_entry.get())

            # Find all image files
            image_files = sorted(
                list(folder_path.glob("*.jpg")) +
                list(folder_path.glob("*.jpeg")) +
                list(folder_path.glob("*.png"))
            )

            if not image_files:
                self.show_error("画像ファイルが見つかりません")
                return

            self.update_pdf_status(f"PDF生成中... ({len(image_files)}枚の画像)")

            # Get settings
            config = self.get_config_from_ui()
            output_path = Path(self.pdf_output_entry.get())
            compression = self.compression_slider.get()

            # Generate PDF
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
                    f"PDFを生成しました！\n\n"
                    f"出力先: {output_path}\n"
                    f"ファイルサイズ: {file_size:.2f} MB\n"
                    f"ページ数: {len(image_files)}"
                )
            else:
                self.show_error("PDF生成に失敗しました")

        except Exception as e:
            logger.error(f"PDF conversion error: {e}", exc_info=True)
            self.show_error(f"処理エラー: {e}")

        finally:
            self.after(0, self.reset_pdf_ui)

    def switch_to_pdf_tab(self, folder_path: Path):
        """Switch to PDF tab and set folder."""
        self.tabview.set("📄 PDF変換")
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
