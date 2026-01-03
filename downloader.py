"""Image downloader with SHA-256 deduplication."""

import os
import requests
from utils import compute_hash, sanitize_filename, get_file_extension
from progress_tracker import ProgressTracker


class ImageDownloader:
    """Downloads images with content-based deduplication."""

    def __init__(
        self,
        output_dir: str,
        progress_tracker: ProgressTracker,
        prefix: str = "pothole"
    ):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save images
            progress_tracker: ProgressTracker instance for state persistence
            prefix: Prefix for image filenames
        """
        self.output_dir = output_dir
        self.tracker = progress_tracker
        self.prefix = prefix

        # Local stats for current batch
        self.batch_stats = {
            'saved': 0,
            'duplicates': 0,
            'errors': 0,
        }

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def download_image(self, url: str) -> tuple[bytes, str] | None:
        """
        Download image from URL.

        Args:
            url: Image URL to download

        Returns:
            Tuple of (content bytes, content type) or None on failure
        """
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            content = response.content

            return content, content_type

        except requests.exceptions.RequestException:
            return None

    def save_image(self, content: bytes, url: str, content_type: str) -> str | None:
        """
        Save image to disk with proper naming.

        Args:
            content: Image bytes
            url: Source URL (for filename)
            content_type: Content-Type header

        Returns:
            Saved filename or None if duplicate/error
        """
        # Compute hash for deduplication
        content_hash = compute_hash(content)

        # Check for duplicate (using tracker's persistent hash set)
        if self.tracker.is_hash_seen(content_hash):
            self.batch_stats['duplicates'] += 1
            self.tracker.increment_duplicates()
            return None

        # Mark as seen (persisted in tracker)
        self.tracker.add_hash(content_hash)

        # Generate filename using tracker's counter
        counter = self.tracker.increment_counter()
        extension = get_file_extension(url, content_type)
        sanitized_url = sanitize_filename(url)
        filename = f"{self.prefix}_{counter:03d}_scraped_from_{sanitized_url}{extension}"

        # Save to disk
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(content)
            self.batch_stats['saved'] += 1
            self.tracker.increment_saved()
            return filename
        except IOError:
            self.batch_stats['errors'] += 1
            self.tracker.increment_errors()
            return None

    def process_image(self, image_data: dict) -> bool:
        """
        Process a single image: download, deduplicate, save.

        Args:
            image_data: Dict with 'url' and 'source' keys

        Returns:
            True if image was saved, False otherwise
        """
        url = image_data.get('url')
        if not url:
            self.batch_stats['errors'] += 1
            self.tracker.increment_errors()
            return False

        # Download
        result = self.download_image(url)
        if result is None:
            self.batch_stats['errors'] += 1
            self.tracker.increment_errors()
            return False

        content, content_type = result

        # Save (with deduplication)
        filename = self.save_image(content, url, content_type)
        return filename is not None

    def process_all(self, images: list[dict], show_progress: bool = True) -> dict:
        """
        Process all images with progress display.

        Args:
            images: List of image metadata dicts
            show_progress: Whether to show progress bar

        Returns:
            Batch statistics dict
        """
        total = len(images)

        if total == 0:
            return self.batch_stats.copy()

        for i, image_data in enumerate(images, 1):
            self.process_image(image_data)

            if show_progress:
                # Simple progress indicator
                progress = int((i / total) * 40)
                bar = '█' * progress + '░' * (40 - progress)
                print(f"\r  Downloading: [{bar}] {i}/{total}", end='', flush=True)

        if show_progress:
            print()  # New line after progress bar

        return self.batch_stats.copy()

    def reset_batch_stats(self):
        """Reset batch statistics for new batch."""
        self.batch_stats = {
            'saved': 0,
            'duplicates': 0,
            'errors': 0,
        }

    def get_batch_stats(self) -> dict:
        """Get current batch statistics."""
        return self.batch_stats.copy()
