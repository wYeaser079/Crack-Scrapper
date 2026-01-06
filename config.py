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
DEFAULT_OUTPUT_DIR = "D:\Personal\Images\Potholes"
DEFAULT_COUNT = 100
DEFAULT_QUERIES_FILE = "queries.txt"
PROGRESS_FILE = "progress.json"

# Filter configurations
DATE_FILTERS = ['d30', 'm6', 'y1', 'y5']
SIZE_FILTERS = ['large', 'xlarge', 'xxlarge', 'huge']

# Default filter mode (set your preference here)
USE_DATE_FILTERS = False  # Set True to enable date filters
USE_SIZE_FILTERS = True   # Set True to enable size filters (recommended)


def load_api_credentials():
    """
    Load CX ID and multiple API keys from environment variables.

    Structure:
        CX = single search engine ID
        API_KEY_1, API_KEY_2, ... = multiple API keys for quota rotation

    Falls back to legacy format (API_KEY_1/CX_1 pairs) for compatibility.

    Returns:
        List of tuples: [(api_key, cx), ...]
    """
    credentials = []

    # New format: Single CX with multiple API keys
    cx = os.getenv("CX")

    if cx:
        # Load all API_KEY_N entries
        index = 1
        while True:
            api_key = os.getenv(f"API_KEY_{index}")
            if api_key:
                credentials.append((api_key, cx))
                index += 1
            else:
                break

        # Also check for unnumbered API_KEY
        if not credentials:
            api_key = os.getenv("API_KEY")
            if api_key:
                credentials.append((api_key, cx))

    # Legacy format: Paired API_KEY_N and CX_N
    if not credentials:
        index = 1
        while True:
            api_key = os.getenv(f"API_KEY_{index}")
            cx_n = os.getenv(f"CX_{index}")

            if api_key and cx_n:
                credentials.append((api_key, cx_n))
                index += 1
            else:
                break

    return credentials


def validate_config():
    """Validate that required configuration is present."""
    credentials = load_api_credentials()

    if not credentials:
        raise ValueError(
            "No API credentials found. Please set CX and API_KEY_1 "
            "(or legacy API_KEY_1/CX_1 pairs) in .env file."
        )

    return credentials
