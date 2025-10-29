"""PDF generation and compression functionality."""

import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import img2pdf
from ..utils.logger import get_logger


logger = get_logger()


# Compression level settings
COMPRESSION_LEVELS = {
    1: {"quality": 95, "scale": 1.00, "est_size_kb": 800},  # High quality
    2: {"quality": 85, "scale": 0.95, "est_size_kb": 500},  # Medium-high
    3: {"quality": 75, "scale": 0.90, "est_size_kb": 300},  # Medium
    4: {"quality": 65, "scale": 0.85, "est_size_kb": 150},  # Medium-low
    5: {"quality": 50, "scale": 0.80, "est_size_kb": 80},   # Low quality
}


class PDFGenerator:
    """Handles PDF generation and optimization."""

    def __init__(self):
        """Initialize PDFGenerator."""
        pass

    def estimate_file_size(
        self,
        page_count: int,
        compression_level: int,
        screenshot_count: int = 1
    ) -> float:
        """
        Estimate final PDF file size in MB.

        Args:
            page_count: Number of pages
            compression_level: Compression level (1-5)
            screenshot_count: Number of screenshots per page

        Returns:
            Estimated size in MB
        """
        settings = COMPRESSION_LEVELS.get(compression_level, COMPRESSION_LEVELS[3])
        size_per_page_kb = settings["est_size_kb"]

        # If saving all screenshots, multiply by count
        total_size_kb = page_count * size_per_page_kb * screenshot_count

        return total_size_kb / 1024  # Convert to MB

    def compress_image(
        self,
        image_path: Path,
        quality: int,
        scale: float,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Compress and resize an image.

        Args:
            image_path: Input image path
            quality: JPEG quality (1-100)
            scale: Scale factor (0.0-1.0)
            output_path: Output path (if None, overwrites input)

        Returns:
            Path to compressed image
        """
        try:
            img = Image.open(image_path)

            # Resize if scale < 1.0
            if scale < 1.0:
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Save with compression
            if output_path is None:
                output_path = image_path

            img.save(output_path, "JPEG", quality=quality, optimize=True)

            logger.info(f"Compressed image: {output_path.name} (quality={quality}, scale={scale})")
            return output_path

        except Exception as e:
            logger.error(f"Failed to compress image {image_path}: {e}")
            return image_path

    def compress_images_batch(
        self,
        image_paths: List[Path],
        compression_level: int
    ) -> List[Path]:
        """
        Compress multiple images based on compression level.

        Args:
            image_paths: List of image paths
            compression_level: Compression level (1-5)

        Returns:
            List of compressed image paths
        """
        settings = COMPRESSION_LEVELS.get(compression_level, COMPRESSION_LEVELS[3])
        quality = settings["quality"]
        scale = settings["scale"]

        compressed_paths = []

        for img_path in image_paths:
            compressed_path = self.compress_image(img_path, quality, scale)
            compressed_paths.append(compressed_path)

        return compressed_paths

    def create_pdf(
        self,
        image_paths: List[Path],
        output_path: Path,
        compression_level: int = 3
    ) -> Tuple[bool, Optional[float]]:
        """
        Create PDF from images.

        Args:
            image_paths: List of image paths (in order)
            output_path: Output PDF path
            compression_level: Compression level (1-5)

        Returns:
            Tuple of (success: bool, file_size_mb: float or None)
        """
        if not image_paths:
            logger.error("No images to create PDF")
            return False, None

        try:
            # Sort images to ensure correct order
            sorted_images = sorted(image_paths, key=lambda p: p.name)

            # Compress images if needed
            if compression_level > 1:
                logger.info(f"Compressing images with level {compression_level}")
                sorted_images = self.compress_images_batch(sorted_images, compression_level)

            # Convert images to PDF
            logger.info(f"Creating PDF with {len(sorted_images)} images")

            with open(output_path, "wb") as f:
                f.write(img2pdf.convert([str(img) for img in sorted_images]))

            # Get file size
            file_size_mb = output_path.stat().st_size / (1024 * 1024)

            logger.info(f"PDF created: {output_path} ({file_size_mb:.2f} MB)")
            return True, file_size_mb

        except Exception as e:
            logger.error(f"Failed to create PDF: {e}")
            return False, None

    def optimize_for_target_size(
        self,
        image_paths: List[Path],
        output_path: Path,
        target_size_mb: float,
        max_attempts: int = 5
    ) -> Tuple[bool, Optional[float]]:
        """
        Create PDF optimized to meet target file size.

        Args:
            image_paths: List of image paths
            output_path: Output PDF path
            target_size_mb: Target size in MB
            max_attempts: Maximum optimization attempts

        Returns:
            Tuple of (success: bool, file_size_mb: float or None)
        """
        logger.info(f"Optimizing PDF for target size: {target_size_mb} MB")

        # Start with medium compression
        compression_level = 3

        for attempt in range(1, max_attempts + 1):
            success, file_size_mb = self.create_pdf(
                image_paths,
                output_path,
                compression_level
            )

            if not success:
                return False, None

            logger.info(f"Attempt {attempt}: {file_size_mb:.2f} MB (target: {target_size_mb} MB)")

            # Check if within target
            if file_size_mb <= target_size_mb:
                logger.info("Target size achieved")
                return True, file_size_mb

            # Increase compression for next attempt
            compression_level = min(5, compression_level + 1)

            if compression_level > 5:
                logger.warning("Max compression reached, target size not achievable")
                break

        # Return final result even if target not met
        return True, file_size_mb

    def get_compression_settings(self, level: int) -> dict:
        """
        Get compression settings for a given level.

        Args:
            level: Compression level (1-5)

        Returns:
            Settings dictionary
        """
        return COMPRESSION_LEVELS.get(level, COMPRESSION_LEVELS[3])

    def estimate_file_size_max_quality(self, page_count: int) -> float:
        """
        Estimate file size with maximum quality (no compression).

        Args:
            page_count: Number of pages

        Returns:
            Estimated size in MB
        """
        # Max quality: approximately 1 MB per page
        return page_count * 1.0

    def create_split_pdfs(
        self,
        image_paths: List[Path],
        base_output_path: Path,
        max_size_mb: float
    ) -> Tuple[bool, List[Path], List[float]]:
        """
        Create multiple PDFs split by file size at maximum quality.

        Args:
            image_paths: List of image paths (in order)
            base_output_path: Base output path (e.g., output.pdf)
            max_size_mb: Maximum size per PDF file in MB

        Returns:
            Tuple of (success: bool, pdf_paths: List[Path], sizes: List[float])
        """
        if not image_paths:
            logger.error("No images to create PDF")
            return False, [], []

        try:
            sorted_images = sorted(image_paths, key=lambda p: p.name)

            # Calculate approximate size per image at max quality
            # Estimate ~1 MB per image at maximum quality
            est_size_per_image = 1.0  # MB

            # Calculate how many images per PDF
            images_per_pdf = max(1, int(max_size_mb / est_size_per_image))

            logger.info(f"Splitting {len(sorted_images)} images into PDFs of ~{images_per_pdf} images each")
            logger.info(f"Target size: {max_size_mb} MB per PDF")

            pdf_paths = []
            pdf_sizes = []

            # Split images into chunks
            for chunk_idx in range(0, len(sorted_images), images_per_pdf):
                chunk_images = sorted_images[chunk_idx:chunk_idx + images_per_pdf]

                # Generate output filename
                if len(sorted_images) <= images_per_pdf:
                    # Only one PDF needed
                    output_path = base_output_path
                else:
                    # Multiple PDFs: output_1.pdf, output_2.pdf, etc.
                    pdf_number = (chunk_idx // images_per_pdf) + 1
                    stem = base_output_path.stem
                    suffix = base_output_path.suffix
                    parent = base_output_path.parent
                    output_path = parent / f"{stem}_{pdf_number}{suffix}"

                logger.info(f"Creating PDF {len(pdf_paths) + 1} with {len(chunk_images)} images")

                # Create PDF with maximum quality (no compression)
                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert([str(img) for img in chunk_images]))

                # Get file size
                file_size_mb = output_path.stat().st_size / (1024 * 1024)

                pdf_paths.append(output_path)
                pdf_sizes.append(file_size_mb)

                logger.info(f"Created: {output_path.name} ({file_size_mb:.2f} MB)")

            total_size = sum(pdf_sizes)
            logger.info(f"Split complete: {len(pdf_paths)} PDF(s), total {total_size:.2f} MB")

            return True, pdf_paths, pdf_sizes

        except Exception as e:
            logger.error(f"Failed to create split PDFs: {e}")
            return False, [], []
