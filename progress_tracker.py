"""Progress tracking and checkpoint/resume system."""

import json
import os
from datetime import datetime
from config import PROGRESS_FILE


class ProgressTracker:
    """Tracks progress and enables resume from checkpoint."""

    def __init__(self, progress_file: str = PROGRESS_FILE):
        """
        Initialize the progress tracker.

        Args:
            progress_file: Path to the progress JSON file
        """
        self.progress_file = progress_file
        self.status = "in_progress"
        self.started_at = None
        self.updated_at = None
        self.queries_file = None
        self.total_queries = 0
        self.total_combinations = 0

        # Current position
        self.query_index = 0
        self.filter_index = 0

        # Completed combinations: set of (query_index, filter_index) tuples
        self.completed = set()

        # Statistics
        self.stats = {
            'images_saved': 0,
            'duplicates_skipped': 0,
            'errors': 0,
        }

        # Deduplication hashes (persisted across runs)
        self.seen_hashes = set()

        # Image counter (persisted across runs)
        self.image_counter = 0

    def load(self) -> bool:
        """
        Load progress from file.

        Returns:
            True if resuming from previous session, False if starting fresh
        """
        if not os.path.exists(self.progress_file):
            self.started_at = datetime.now().isoformat()
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if previous session was completed
            if data.get('status') == 'completed':
                self.started_at = datetime.now().isoformat()
                return False

            # Resume from previous session
            self.status = data.get('status', 'in_progress')
            self.started_at = data.get('started_at')
            self.updated_at = data.get('updated_at')
            self.queries_file = data.get('queries_file')
            self.total_queries = data.get('total_queries', 0)
            self.total_combinations = data.get('total_combinations', 0)

            # Load position
            position = data.get('current_position', {})
            self.query_index = position.get('query_index', 0)
            self.filter_index = position.get('filter_index', 0)

            # Load completed combinations
            completed_list = data.get('completed', [])
            self.completed = set(
                (item['query_index'], item['filter_index'])
                for item in completed_list
            )

            # Load stats
            self.stats = data.get('stats', {
                'images_saved': 0,
                'duplicates_skipped': 0,
                'errors': 0,
            })

            # Load hashes for deduplication
            self.seen_hashes = set(data.get('seen_hashes', []))

            # Load image counter
            self.image_counter = data.get('image_counter', 0)

            return True

        except (json.JSONDecodeError, IOError):
            self.started_at = datetime.now().isoformat()
            return False

    def save(self):
        """Save current progress to file."""
        self.updated_at = datetime.now().isoformat()

        data = {
            'status': self.status,
            'started_at': self.started_at,
            'updated_at': self.updated_at,
            'queries_file': self.queries_file,
            'total_queries': self.total_queries,
            'total_combinations': self.total_combinations,
            'current_position': {
                'query_index': self.query_index,
                'filter_index': self.filter_index,
            },
            'completed': [
                {'query_index': q, 'filter_index': f}
                for q, f in sorted(self.completed)
            ],
            'stats': self.stats,
            'seen_hashes': list(self.seen_hashes),
            'image_counter': self.image_counter,
        }

        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def set_session_info(self, queries_file: str, total_queries: int, total_combinations: int):
        """Set session information."""
        self.queries_file = queries_file
        self.total_queries = total_queries
        self.total_combinations = total_combinations

    def update_position(self, query_index: int, filter_index: int):
        """Update current position."""
        self.query_index = query_index
        self.filter_index = filter_index

    def mark_combination_complete(self, query_index: int, filter_index: int):
        """Mark a combination as completed."""
        self.completed.add((query_index, filter_index))
        self.update_position(query_index, filter_index)

    def is_combination_done(self, query_index: int, filter_index: int) -> bool:
        """Check if a combination was already processed."""
        return (query_index, filter_index) in self.completed

    def mark_finished(self):
        """Mark the entire session as completed."""
        self.status = 'completed'
        self.save()

    def add_hash(self, hash_value: str):
        """Add a hash to the seen set."""
        self.seen_hashes.add(hash_value)

    def is_hash_seen(self, hash_value: str) -> bool:
        """Check if a hash was already seen."""
        return hash_value in self.seen_hashes

    def increment_counter(self) -> int:
        """Increment and return the next image number."""
        self.image_counter += 1
        return self.image_counter

    def increment_saved(self):
        """Increment saved images count."""
        self.stats['images_saved'] += 1

    def increment_duplicates(self):
        """Increment duplicates count."""
        self.stats['duplicates_skipped'] += 1

    def increment_errors(self):
        """Increment errors count."""
        self.stats['errors'] += 1

    def get_resume_point(self) -> tuple[int, int]:
        """Get the point to resume from."""
        return (self.query_index, self.filter_index)

    def get_stats(self) -> dict:
        """Get current statistics."""
        return self.stats.copy()

    def get_progress_display(self) -> dict:
        """Get progress information for display."""
        return {
            'status': self.status,
            'started_at': self.started_at,
            'updated_at': self.updated_at,
            'query_index': self.query_index,
            'filter_index': self.filter_index,
            'completed_count': len(self.completed),
            'total_combinations': self.total_combinations,
            'images_saved': self.stats['images_saved'],
            'hashes_loaded': len(self.seen_hashes),
        }
