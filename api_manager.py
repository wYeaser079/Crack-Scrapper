"""API key manager with rotation and quota tracking."""


class APIManager:
    """Manages multiple API keys with automatic rotation on quota exhaustion."""

    def __init__(self, credentials: list[tuple[str, str]]):
        """
        Initialize the API manager.

        Args:
            credentials: List of (api_key, cx) tuples
        """
        if not credentials:
            raise ValueError("At least one API key/CX pair is required")

        self.credentials = credentials
        self.current_index = 0
        self.exhausted_indices = set()

    def get_current_credentials(self) -> tuple[str, str]:
        """
        Get the current API key and CX pair.

        Returns:
            Tuple of (api_key, cx)
        """
        return self.credentials[self.current_index]

    def get_current_key_number(self) -> int:
        """Get the current key number (1-based for display)."""
        return self.current_index + 1

    def get_total_keys(self) -> int:
        """Get total number of API keys."""
        return len(self.credentials)

    def mark_current_exhausted(self):
        """Mark the current API key as quota exhausted."""
        self.exhausted_indices.add(self.current_index)

    def rotate_to_next(self) -> bool:
        """
        Rotate to the next available API key.

        Returns:
            True if successfully rotated, False if all keys exhausted
        """
        # Mark current as exhausted
        self.mark_current_exhausted()

        # Find next available key
        for i in range(len(self.credentials)):
            next_index = (self.current_index + 1 + i) % len(self.credentials)
            if next_index not in self.exhausted_indices:
                self.current_index = next_index
                return True

        return False

    def has_available_keys(self) -> bool:
        """Check if any API keys are still available."""
        return len(self.exhausted_indices) < len(self.credentials)

    def reset_exhausted(self):
        """Reset all keys to available (for new day)."""
        self.exhausted_indices.clear()
        self.current_index = 0

    def get_status(self) -> dict:
        """Get current status for display."""
        return {
            'current_key': self.current_index + 1,
            'total_keys': len(self.credentials),
            'exhausted_count': len(self.exhausted_indices),
            'available_count': len(self.credentials) - len(self.exhausted_indices),
        }
