"""
Pothole Image Scraper

A tool to search and download pothole images using Google Custom Search API
with automatic deduplication, multi-key rotation, and resume support.
"""

import argparse
import sys
import os
from config import validate_config, DEFAULT_OUTPUT_DIR, DEFAULT_COUNT, DEFAULT_QUERIES_FILE, USE_DATE_FILTERS, USE_SIZE_FILTERS
from utils import read_queries_from_file
from api_manager import APIManager
from progress_tracker import ProgressTracker
from searcher import (
    search_images,
    generate_filter_combinations,
    format_filter_display,
    AllKeysExhaustedError
)
from downloader import ImageDownloader


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Search and download pothole images with deduplication.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py                        # Run with defaults (size filters only)
  python main.py --count 50             # Fetch 50 images per filter
  python main.py --no-filters           # No filters, just base queries
  python main.py --date-only            # Use date filters instead
  python main.py --fresh                # Ignore progress, start fresh
        '''
    )

    parser.add_argument(
        '--queries',
        default=DEFAULT_QUERIES_FILE,
        help=f'Path to text file containing search queries (default: {DEFAULT_QUERIES_FILE})'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=DEFAULT_COUNT,
        help=f'Maximum images to fetch per filter combination (default: {DEFAULT_COUNT}, max: 100)'
    )

    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for images (default: {DEFAULT_OUTPUT_DIR})'
    )

    parser.add_argument(
        '--prefix',
        default='pothole',
        help='Prefix for image filenames (default: pothole)'
    )

    parser.add_argument(
        '--no-filters',
        action='store_true',
        help='Skip all filters (use only base queries)'
    )

    parser.add_argument(
        '--date-only',
        action='store_true',
        help='Use only date filters, skip size filters'
    )

    parser.add_argument(
        '--size-only',
        action='store_true',
        help='Use only size filters, skip date filters'
    )

    parser.add_argument(
        '--fresh',
        action='store_true',
        help='Ignore progress.json and start fresh'
    )

    return parser.parse_args()


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_resume_info(tracker: ProgressTracker):
    """Print resume information."""
    info = tracker.get_progress_display()
    print_header("RESUMING FROM PREVIOUS SESSION")
    print(f"  Last run: {info['updated_at']}")
    print(f"  Progress: Query {info['query_index'] + 1}, Filter {info['filter_index'] + 1}")
    print(f"  Combinations completed: {info['completed_count']}/{info['total_combinations']}")
    print(f"  Images saved: {info['images_saved']}")
    print(f"  Hashes loaded: {info['hashes_loaded']} (for deduplication)")


def print_completion_info(tracker: ProgressTracker):
    """Print previous completion info."""
    info = tracker.get_progress_display()
    print_header("PREVIOUS SESSION COMPLETED")
    print(f"  Completed: {info['updated_at']}")
    print(f"  Images saved: {info['images_saved']}")
    print("\nStarting fresh run...")


def main():
    """Main entry point."""
    args = parse_args()

    # Validate configuration and get credentials
    print("Validating configuration...")
    try:
        credentials = validate_config()
        print(f"Loaded {len(credentials)} API key pair(s)")
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize API manager
    api_manager = APIManager(credentials)

    # Read queries from file
    print(f"Loading queries from {args.queries}...")
    try:
        queries = read_queries_from_file(args.queries)
    except FileNotFoundError:
        print(f"Error: Queries file not found: {args.queries}")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading queries file: {e}")
        sys.exit(1)

    if not queries:
        print("Error: No queries found in file.")
        sys.exit(1)

    print(f"Found {len(queries)} queries")

    # Determine filter combinations
    # Use config defaults, but allow command line overrides
    if args.no_filters:
        use_date = False
        use_size = False
    elif args.date_only:
        use_date = True
        use_size = False
    elif args.size_only:
        use_date = False
        use_size = True
    else:
        # Use defaults from config.py
        use_date = USE_DATE_FILTERS
        use_size = USE_SIZE_FILTERS

    if not use_date and not use_size:
        filter_combinations = [{}]  # Single empty filter
    else:
        filter_combinations = generate_filter_combinations(use_date, use_size)

    total_combinations = len(queries) * len(filter_combinations)
    print(f"Filter combinations per query: {len(filter_combinations)}")
    print(f"Total combinations: {total_combinations}")

    # Initialize progress tracker
    tracker = ProgressTracker()

    # Handle fresh start or resume
    if args.fresh:
        # Delete existing progress file
        if os.path.exists(tracker.progress_file):
            os.remove(tracker.progress_file)
        print("Starting fresh (--fresh flag used)")
        is_resuming = False
    else:
        is_resuming = tracker.load()

    # Set session info
    tracker.set_session_info(args.queries, len(queries), total_combinations)

    # Show resume or completion info
    if is_resuming:
        print_resume_info(tracker)
    elif tracker.status == 'completed' and not args.fresh:
        print_completion_info(tracker)
        # Reset for fresh run
        tracker = ProgressTracker()
        tracker.set_session_info(args.queries, len(queries), total_combinations)

    # Clamp count to valid range
    count = min(max(1, args.count), 100)

    # Initialize downloader with tracker
    downloader = ImageDownloader(args.output, tracker, prefix=args.prefix)

    # Main processing loop
    print_header("PROCESSING")

    all_keys_exhausted = False
    filter_counter = 0

    try:
        for query_idx, query in enumerate(queries):
            print(f"\n{'─' * 60}")
            print(f"[Query {query_idx + 1}/{len(queries)}] \"{query}\"")
            print(f"{'─' * 60}")

            for filter_idx, filters in enumerate(filter_combinations):
                filter_counter += 1

                # Skip if already completed
                if tracker.is_combination_done(query_idx, filter_idx):
                    print(f"\n[Filter {filter_idx + 1}/{len(filter_combinations)}] {format_filter_display(filters)}")
                    print("  Skipped (already completed)")
                    continue

                # Update position
                tracker.update_position(query_idx, filter_idx)

                print(f"\n[Filter {filter_idx + 1}/{len(filter_combinations)}] {format_filter_display(filters)}")
                print(f"  Using API Key #{api_manager.get_current_key_number()}")

                # Search for images
                try:
                    images = search_images(query, api_manager, filters, count)
                except AllKeysExhaustedError:
                    print("\n[!] All API keys exhausted!")
                    all_keys_exhausted = True
                    break

                # Handle network/API errors (None = error, can retry)
                if images is None:
                    print("  Skipping due to error (will retry on next run)")
                    tracker.increment_errors()
                    tracker.save()
                    continue

                # Handle no results found (empty list = success but no results)
                if not images:
                    print("  No images found for this combination")
                    tracker.add_no_results(query_idx, filter_idx, query, filters)
                    tracker.mark_combination_complete(query_idx, filter_idx)
                    tracker.save()
                    continue

                print(f"  Found: {len(images)} images")

                # Download images
                downloader.reset_batch_stats()
                batch_stats = downloader.process_all(images)

                print(f"  Saved: {batch_stats['saved']} | Duplicates: {batch_stats['duplicates']} | Errors: {batch_stats['errors']}")

                # Mark as complete and save progress
                tracker.mark_combination_complete(query_idx, filter_idx)
                tracker.save()

            if all_keys_exhausted:
                break

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        print("[!] Saving progress...")
        tracker.save()

    # Final summary
    stats = tracker.get_stats()

    if all_keys_exhausted:
        print_header("PAUSED - QUOTA EXHAUSTED")
        print(f"  Progress saved: Query {tracker.query_index + 1}, Filter {tracker.filter_index + 1}")
        print(f"  Combinations completed: {len(tracker.completed)}/{total_combinations}")
        print(f"  Images saved so far: {stats['images_saved']}")
        print(f"  Run again later to continue.")
    else:
        # Mark as finished
        tracker.mark_finished()
        print_header("COMPLETED")

    print_header("SUMMARY")
    print(f"  Total combinations: {total_combinations}")
    print(f"  Completed: {len(tracker.completed)}")
    print(f"  Unique images saved: {stats['images_saved']}")
    print(f"  Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"  No results found: {stats['no_results']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  API keys used: {api_manager.get_status()['exhausted_count'] + 1} of {api_manager.get_total_keys()}")
    print(f"  Output directory: {args.output}")

    # Show no-results details if any
    if tracker.no_results_list:
        print(f"\n  Combinations with no results ({len(tracker.no_results_list)}):")
        for item in tracker.no_results_list:
            print(f"    - Query: \"{item['query']}\" | Filter: {item['filters']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
