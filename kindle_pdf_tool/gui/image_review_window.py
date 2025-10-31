"""Image review window for manual image selection and deletion."""

import os
import threading
from pathlib import Path
from typing import List, Optional
from tkinter import messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
import customtkinter as ctk
from PIL import Image

from ..utils.logger import get_logger


logger = get_logger()

JP_FONT = ("Yu Gothic UI", 11)
JP_FONT_BOLD = ("Yu Gothic UI", 12, "bold")


class ImageReviewWindow(ctk.CTkToplevel):
    """Window for reviewing and deleting captured screenshots."""

    def __init__(self, parent, image_folder: Path, callback=None):
        """
        Initialize image review window.

        Args:
            parent: Parent window
            image_folder: Folder containing images
            callback: Callback function when done
        """
        super().__init__(parent)

        self.image_folder = image_folder
        self.callback = callback
        self.image_files: List[Path] = []
        self.selected_images: set = set()
        self.image_widgets: dict = {}  # Store widget references for fast deletion
        self.loading_in_progress = False  # Track if images are being loaded

        # Window settings
        self.title("画像確認・削除")
        self.geometry("900x700")
        self.resizable(True, True)

        # Make it modal
        self.transient(parent)
        self.grab_set()

        # Build UI
        self.build_ui()

        # Load images
        self.load_images()

        logger.info(f"Image review window opened for {image_folder}")

    def build_ui(self):
        """Build user interface."""
        # Main container
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Top frame: Info and range deletion
        top_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)

        # Info label
        self.info_label = ctk.CTkLabel(
            top_frame,
            text="画像を確認して不要なものを削除できます",
            font=JP_FONT,
            text_color="gray"
        )
        self.info_label.pack(side="left", padx=10)

        self.count_label = ctk.CTkLabel(
            top_frame,
            text="画像数: 0枚",
            font=JP_FONT_BOLD
        )
        self.count_label.pack(side="right", padx=10)

        # Range deletion frame
        range_frame = ctk.CTkFrame(main_container)
        range_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            range_frame,
            text="━ 範囲削除 ━",
            font=JP_FONT_BOLD
        ).pack(pady=5)

        range_input_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
        range_input_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(range_input_frame, text="ページ", font=JP_FONT).pack(side="left", padx=(0, 5))

        self.start_page_entry = ctk.CTkEntry(range_input_frame, width=70)
        self.start_page_entry.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(range_input_frame, text="〜", font=JP_FONT).pack(side="left", padx=(0, 5))

        self.end_page_entry = ctk.CTkEntry(range_input_frame, width=70)
        self.end_page_entry.pack(side="left", padx=(0, 10))

        self.delete_range_btn = ctk.CTkButton(
            range_input_frame,
            text="範囲削除",
            width=100,
            command=self.delete_range,
            font=JP_FONT
        )
        self.delete_range_btn.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            range_input_frame,
            text="（例: 5〜10 でページ5-10を削除）",
            font=("Yu Gothic UI", 9),
            text_color="gray"
        ).pack(side="left")

        # Progress bar frame
        self.progress_frame = ctk.CTkFrame(main_container)
        self.progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="画像を読み込み中...",
            font=JP_FONT
        )
        self.progress_label.pack(pady=(5, 2))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=840
        )
        self.progress_bar.pack(padx=10, pady=(0, 5))
        self.progress_bar.set(0)

        # Hide progress initially
        self.progress_frame.pack_forget()

        # Scrollable image grid
        self.scroll_frame = ctk.CTkScrollableFrame(
            main_container,
            width=860,
            height=480
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom buttons
        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=5)

        self.delete_selected_btn = ctk.CTkButton(
            button_frame,
            text="選択削除",
            width=120,
            height=36,
            command=self.delete_selected,
            font=JP_FONT_BOLD
        )
        self.delete_selected_btn.pack(side="left", padx=(180, 10))

        self.open_folder_btn = ctk.CTkButton(
            button_frame,
            text="フォルダを開く",
            width=140,
            height=36,
            command=self.open_folder,
            font=JP_FONT_BOLD
        )
        self.open_folder_btn.pack(side="left", padx=(0, 10))

        self.done_btn = ctk.CTkButton(
            button_frame,
            text="完了",
            width=120,
            height=36,
            command=self.on_done,
            font=JP_FONT_BOLD,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.done_btn.pack(side="left")

    def load_images(self):
        """Load images from folder."""
        try:
            # Find all image files
            self.image_files = sorted(
                list(self.image_folder.glob("*.jpg")) +
                list(self.image_folder.glob("*.jpeg")) +
                list(self.image_folder.glob("*.png"))
            )

            if not self.image_files:
                messagebox.showwarning("警告", "画像ファイルが見つかりません")
                self.destroy()
                return

            # Update count
            self.count_label.configure(text=f"画像数: {len(self.image_files)}枚")

            # Display images in background thread
            self.display_images()

        except Exception as e:
            logger.error(f"Failed to load images: {e}")
            messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")

    def display_images(self):
        """Start background thread to display images."""
        if self.loading_in_progress:
            return

        self.loading_in_progress = True

        # Show progress bar
        self.progress_frame.pack(fill="x", padx=5, pady=5, before=self.scroll_frame)
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"画像を読み込み中... 0/{len(self.image_files)}")

        # Start background thread
        thread = threading.Thread(target=self.display_images_threaded, daemon=True)
        thread.start()

    def display_images_threaded(self):
        """Display images in grid using parallel processing."""
        try:
            # Clear existing widgets (on main thread)
            self.after(0, self._clear_widgets)

            columns = 4
            thumbnail_size = (120, 160)
            total_images = len(self.image_files)

            # Helper function to create thumbnail
            def create_thumbnail(idx_and_path):
                idx, img_path = idx_and_path
                try:
                    img = Image.open(img_path)
                    img.thumbnail(thumbnail_size, Image.Resampling.BILINEAR)
                    return (idx, img_path, img, None)
                except Exception as e:
                    logger.error(f"Failed to load thumbnail {img_path}: {e}")
                    return (idx, img_path, None, str(e))

            # Process images in parallel (use 4 workers)
            loaded_count = 0
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(create_thumbnail, (idx, img_path)): (idx, img_path)
                    for idx, img_path in enumerate(self.image_files)
                }

                # Process completed tasks
                for future in as_completed(futures):
                    idx, img_path, img, error = future.result()

                    # Update UI on main thread
                    self.after(0, self._add_image_widget, idx, img_path, img, error, thumbnail_size, columns)

                    # Update progress
                    loaded_count += 1
                    progress = loaded_count / total_images
                    self.after(0, self._update_progress, loaded_count, total_images, progress)

            # Hide progress bar and configure grid
            self.after(0, self._finalize_display, columns)

        except Exception as e:
            logger.error(f"Failed to display images: {e}")
            self.after(0, lambda: messagebox.showerror("エラー", f"画像表示エラー: {e}"))

        finally:
            self.loading_in_progress = False

    def _clear_widgets(self):
        """Clear existing widgets."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.image_widgets.clear()

    def _add_image_widget(self, idx, img_path, img, error, thumbnail_size, columns):
        """Add single image widget to grid."""
        row = idx // columns
        col = idx % columns

        # Create frame for each image
        img_frame = ctk.CTkFrame(self.scroll_frame, width=140, height=220)
        img_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Store widget reference
        self.image_widgets[img_path] = img_frame

        # Page number label
        page_num = self.extract_page_number(img_path)
        page_label = ctk.CTkLabel(
            img_frame,
            text=f"ページ {page_num}",
            font=JP_FONT_BOLD
        )
        page_label.pack(pady=(5, 2))

        # Thumbnail or error
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=thumbnail_size
            )
            img_label = ctk.CTkLabel(img_frame, image=ctk_img, text="")
            img_label.pack(pady=2)
        else:
            error_label = ctk.CTkLabel(
                img_frame,
                text="画像エラー",
                width=thumbnail_size[0],
                height=thumbnail_size[1]
            )
            error_label.pack(pady=2)

        # Checkbox for selection
        var = ctk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            img_frame,
            text="削除",
            variable=var,
            command=lambda p=img_path, v=var: self.on_image_select(p, v),
            font=JP_FONT
        )
        checkbox.pack(pady=(2, 5))

    def _update_progress(self, loaded_count, total_images, progress):
        """Update progress bar."""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"画像を読み込み中... {loaded_count}/{total_images}")

    def _finalize_display(self, columns):
        """Finalize display after loading complete."""
        # Configure grid weights
        for i in range(columns):
            self.scroll_frame.grid_columnconfigure(i, weight=1)

        # Hide progress bar
        self.progress_frame.pack_forget()

        logger.info(f"Loaded {len(self.image_files)} images")

    def extract_page_number(self, img_path: Path) -> int:
        """Extract page number from filename."""
        try:
            # Assuming format: page_0001.jpg or page_0001_1.jpg
            parts = img_path.stem.split('_')
            if len(parts) >= 2:
                return int(parts[1])
            return 0
        except Exception:
            return 0

    def on_image_select(self, img_path: Path, var: ctk.BooleanVar):
        """Handle image selection."""
        if var.get():
            self.selected_images.add(img_path)
        else:
            self.selected_images.discard(img_path)

    def delete_selected(self):
        """Delete selected images."""
        if not self.selected_images:
            messagebox.showinfo("情報", "削除する画像を選択してください")
            return

        # Confirm
        result = messagebox.askyesno(
            "確認",
            f"{len(self.selected_images)}枚の画像を削除しますか？"
        )

        if result:
            try:
                deleted_count = len(self.selected_images)

                for img_path in self.selected_images:
                    # Delete file
                    img_path.unlink()
                    logger.info(f"Deleted: {img_path}")

                    # Remove from list
                    if img_path in self.image_files:
                        self.image_files.remove(img_path)

                    # Destroy widget (fast, no reload needed)
                    if img_path in self.image_widgets:
                        self.image_widgets[img_path].destroy()
                        del self.image_widgets[img_path]

                self.selected_images.clear()

                # Update count label only (no reload)
                self.count_label.configure(text=f"画像数: {len(self.image_files)}枚")

                messagebox.showinfo("完了", f"{deleted_count}枚の画像を削除しました")

            except Exception as e:
                logger.error(f"Failed to delete images: {e}")
                messagebox.showerror("エラー", f"削除に失敗しました: {e}")

    def delete_range(self):
        """Delete images in specified page range."""
        try:
            start_page = int(self.start_page_entry.get())
            end_page = int(self.end_page_entry.get())

            if start_page > end_page:
                messagebox.showerror("エラー", "開始ページは終了ページ以下にしてください")
                return

            # Find images in range
            images_to_delete = []
            for img_path in self.image_files:
                page_num = self.extract_page_number(img_path)
                if start_page <= page_num <= end_page:
                    images_to_delete.append(img_path)

            if not images_to_delete:
                messagebox.showinfo("情報", "指定範囲に画像がありません")
                return

            # Confirm
            result = messagebox.askyesno(
                "確認",
                f"ページ {start_page}〜{end_page} の画像\n"
                f"（{len(images_to_delete)}枚）を削除しますか？"
            )

            if result:
                deleted_count = len(images_to_delete)

                for img_path in images_to_delete:
                    # Delete file
                    img_path.unlink()
                    logger.info(f"Deleted: {img_path}")

                    # Remove from list
                    if img_path in self.image_files:
                        self.image_files.remove(img_path)

                    # Destroy widget (fast, no reload needed)
                    if img_path in self.image_widgets:
                        self.image_widgets[img_path].destroy()
                        del self.image_widgets[img_path]

                # Clear entries
                self.start_page_entry.delete(0, "end")
                self.end_page_entry.delete(0, "end")

                # Update count label only (no reload)
                self.count_label.configure(text=f"画像数: {len(self.image_files)}枚")

                messagebox.showinfo("完了", f"{deleted_count}枚の画像を削除しました")

        except ValueError:
            messagebox.showerror("エラー", "ページ番号は数値で入力してください")
        except Exception as e:
            logger.error(f"Failed to delete range: {e}")
            messagebox.showerror("エラー", f"削除に失敗しました: {e}")

    def open_folder(self):
        """Open image folder in file explorer."""
        try:
            if os.name == 'nt':
                os.startfile(self.image_folder)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', str(self.image_folder)])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            messagebox.showerror("エラー", f"フォルダを開けません: {e}")

    def on_done(self):
        """Handle done button."""
        remaining_images = (
            list(self.image_folder.glob("*.jpg")) +
            list(self.image_folder.glob("*.jpeg")) +
            list(self.image_folder.glob("*.png"))
        )
        remaining_count = len(remaining_images)

        if remaining_count == 0:
            messagebox.showwarning("警告", "画像が1枚もありません")
            return

        logger.info(f"Image review completed. Remaining: {remaining_count} images")

        # Call callback if provided
        if self.callback:
            self.callback()

        # Close window
        self.destroy()
