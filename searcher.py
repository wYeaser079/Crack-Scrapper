"""Google Custom Search API integration for image search."""

import requests
from config import BASE_URL, RESULTS_PER_PAGE, MAX_RESULTS_PER_QUERY, DATE_FILTERS, SIZE_FILTERS
from api_manager import APIManager


class QuotaExhaustedError(Exception):
    """Raised when API quota is exhausted."""
    pass


class AllKeysExhaustedError(Exception):
    """Raised when all API keys are exhausted."""
    pass


def generate_filter_combinations(
    use_date_filters: bool = True,
    use_size_filters: bool = True
) -> list[dict]:
    """
    Generate all filter combinations.

    Args:
        use_date_filters: Whether to include date filters
        use_size_filters: Whether to include size filters

    Returns:
        List of filter dicts, e.g., [{'dateRestrict': 'd30', 'imgSize': 'large'}, ...]
    """
    date_filters = DATE_FILTERS if use_date_filters else [None]
    size_filters = SIZE_FILTERS if use_size_filters else [None]

    combinations = []
    for date_filter in date_filters:
        for size_filter in size_filters:
            combo = {}
            if date_filter:
                combo['dateRestrict'] = date_filter
            if size_filter:
                combo['imgSize'] = size_filter
            combinations.append(combo)

    return combinations


def search_images(
    query: str,
    api_manager: APIManager,
    filters: dict = None,
    count: int = 100
) -> tuple[list[dict], bool]:
    """
    Search for images using Google Custom Search API.

    Args:
        query: The search query string
        api_manager: APIManager instance for credentials
        filters: Dict with optional 'dateRestrict' and 'imgSize' keys
        count: Number of images to fetch (max 100)

    Returns:
        Tuple of (results list, quota_exhausted flag)

    Raises:
        AllKeysExhaustedError: When all API keys are exhausted
    """
    count = min(count, MAX_RESULTS_PER_QUERY)
    filters = filters or {}

    results = []
    start_index = 1

    while len(results) < count:
        if not api_manager.has_available_keys():
            raise AllKeysExhaustedError("All API keys have been exhausted")

        api_key, cx = api_manager.get_current_credentials()
        num_to_fetch = min(RESULTS_PER_PAGE, count - len(results))

        params = {
            'key': api_key,
            'cx': cx,
            'q': query,
            'searchType': 'image',
            'start': start_index,
            'num': num_to_fetch,
        }

        # Add optional filters
        if 'dateRestrict' in filters:
            params['dateRestrict'] = filters['dateRestrict']
        if 'imgSize' in filters:
            params['imgSize'] = filters['imgSize']

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)

            # Check for quota exceeded (429 or specific error)
            if response.status_code == 429:
                print(f"\n  [!] API Key #{api_manager.get_current_key_number()} quota exceeded.")
                if api_manager.rotate_to_next():
                    print(f"  [>] Rotating to API Key #{api_manager.get_current_key_number()}...")
                    continue  # Retry with new key
                else:
                    raise AllKeysExhaustedError("All API keys have been exhausted")

            # Check for other quota-related errors in response
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    error_reason = error_data.get('error', {}).get('errors', [{}])[0].get('reason', '')
                    if error_reason in ['dailyLimitExceeded', 'userRateLimitExceeded', 'quotaExceeded']:
                        print(f"\n  [!] API Key #{api_manager.get_current_key_number()} quota exceeded ({error_reason}).")
                        if api_manager.rotate_to_next():
                            print(f"  [>] Rotating to API Key #{api_manager.get_current_key_number()}...")
                            continue
                        else:
                            raise AllKeysExhaustedError("All API keys have been exhausted")
                except (ValueError, KeyError):
                    pass

            response.raise_for_status()
            data = response.json()

            items = data.get('items', [])
            if not items:
                break

            for item in items:
                results.append({
                    'url': item.get('link'),
                    'source': item.get('image', {}).get('contextLink', ''),
                    'title': item.get('title', ''),
                })

            start_index += RESULTS_PER_PAGE

            if start_index > MAX_RESULTS_PER_QUERY:
                break

        except requests.exceptions.RequestException as e:
            print(f"  API request failed: {e}")
            break
        except ValueError as e:
            print(f"  Failed to parse API response: {e}")
            break

    return results


def format_filter_display(filters: dict) -> str:
    """Format filters for display."""
    if not filters:
        return "no filters"

    parts = []
    if 'dateRestrict' in filters:
        parts.append(f"dateRestrict={filters['dateRestrict']}")
    if 'imgSize' in filters:
        parts.append(f"imgSize={filters['imgSize']}")

    return ", ".join(parts) if parts else "no filters"
