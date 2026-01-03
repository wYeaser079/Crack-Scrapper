"""Configuration module for the pothole image scraper."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API settings
BASE_URL = "https://www.googleapis.com/customsearch/v1"
RESULTS_PER_PAGE = 10
MAX_RESULTS_PER_QUERY = 100

# Default settings
DEFAULT_OUTPUT_DIR = "./image/potholes"
DEFAULT_COUNT = 100
PROGRESS_FILE = "progress.json"

# Filter configurations
DATE_FILTERS = ['d30', 'm6', 'y1', 'y5']
SIZE_FILTERS = ['large', 'xlarge', 'xxlarge', 'huge']


def load_api_credentials():
    """
    Load multiple API key and CX pairs from environment variables.

    Looks for API_KEY_1, CX_1, API_KEY_2, CX_2, etc.
    Falls back to API_KEY, CX if numbered versions not found.

    Returns:
        List of tuples: [(api_key, cx), ...]
    """
    credentials = []

    # Try numbered credentials first (API_KEY_1, CX_1, etc.)
    index = 1
    while True:
        api_key = os.getenv(f"API_KEY_{index}")
        cx = os.getenv(f"CX_{index}")

        if api_key and cx:
            credentials.append((api_key, cx))
            index += 1
        else:
            break

    # Fall back to single API_KEY, CX if no numbered ones found
    if not credentials:
        api_key = os.getenv("API_KEY")
        cx = os.getenv("CX")
        if api_key and cx:
            credentials.append((api_key, cx))

    return credentials


def validate_config():
    """Validate that required configuration is present."""
    credentials = load_api_credentials()

    if not credentials:
        raise ValueError(
            "No API credentials found. Please set API_KEY_1 and CX_1 "
            "(or API_KEY and CX) in .env file."
        )

    return credentials
