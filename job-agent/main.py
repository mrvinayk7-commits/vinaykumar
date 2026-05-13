#!/usr/bin/env python3
"""
Job Search AI Agent
Automatically searches for job postings from the last 24 hours,
filters them based on your profile, scores relevance, and notifies you.

Usage:
    python main.py search          # Run a single search
    python main.py search --apply  # Search and mark top matches for application
    python main.py stats           # Show tracking statistics
    python main.py schedule        # Run on a schedule (every 24 hours)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agent.job_searcher import JobSearcher
from agent.job_filter import JobFilter
from agent.resume_matcher import ResumeMatcher
from agent.job_tracker import JobTracker
from agent.notifier import Notifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("job-agent")


def load_config(config_path: str = "config.yaml") -> dict:
    """Load the main configuration file."""
    path = Path(config_path)
    if not path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)

    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_profile(profile_path: str = "data/profile.yaml") -> dict:
    """Load the user profile."""
    path = Path(profile_path)
    if not path.exists():
        logger.error("Profile file not found: %s", profile_path)
        logger.error("Please copy data/profile.yaml.example to data/profile.yaml and fill in your details")
        sys.exit(1)

    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_search(config: dict, profile: dict, auto_apply: bool = False, min_score: float = 0.6):
    """Run a single job search cycle."""
    logger.info("Starting job search...")

    # 1. Search for jobs from all sources
    searcher = JobSearcher(config)
    all_jobs = searcher.search_all()

    if not all_jobs:
        logger.info("No jobs found from any source. Check your API keys and search criteria.")
        return

    # 2. Filter jobs based on preferences
    job_filter = JobFilter(profile, config.get("search", {}))
    filtered_jobs = job_filter.filter_jobs(all_jobs)

    # 3. Track and deduplicate
    tracker = JobTracker(config)
    new_jobs = tracker.get_new_jobs(filtered_jobs)

    # Mark all new jobs as seen
    for job in new_jobs:
        tracker.mark_seen(job)

    # 4. Score and rank by relevance
    matcher = ResumeMatcher(profile, config)
    ranked_jobs = matcher.rank_jobs(new_jobs)

    # 5. Auto-apply to top matches if enabled
    if auto_apply:
        top_matches = [(job, score) for job, score in ranked_jobs if score >= min_score]
        logger.info("Auto-apply mode: %d jobs above %.0f%% threshold", len(top_matches), min_score * 100)

        for job, score in top_matches:
            if not tracker.is_applied(job):
                # Generate cover letter if AI is available
                cover_letter = matcher.generate_cover_letter(job)

                # Mark as applied (actual application would need platform-specific integration)
                tracker.mark_applied(job, method="agent", cover_letter=cover_letter)
                logger.info(
                    "Prepared application for: %s @ %s (score: %.0f%%)",
                    job.title,
                    job.company,
                    score * 100,
                )

    # 6. Send notifications
    notifier = Notifier(config)
    stats = tracker.get_stats()
    notifier.notify(ranked_jobs, stats)

    logger.info("Search complete. Found %d new jobs.", len(new_jobs))


def show_stats(config: dict):
    """Display tracking statistics."""
    tracker = JobTracker(config)
    stats = tracker.get_stats()

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print("\n[bold]Job Search Agent Statistics[/bold]\n")
        console.print(f"  Total jobs seen:    {stats['total_seen']}")
        console.print(f"  Total applied:      {stats['total_applied']}")
        console.print(f"\n  [bold]By Status:[/bold]")
        for status, count in stats.get("by_status", {}).items():
            console.print(f"    {status}: {count}")
        console.print()
    except ImportError:
        print("\nJob Search Agent Statistics")
        print(f"  Total jobs seen:  {stats['total_seen']}")
        print(f"  Total applied:    {stats['total_applied']}")
        print(f"  By Status: {stats.get('by_status', {})}")
        print()


def run_scheduled(config: dict, profile: dict):
    """Run the agent on a schedule."""
    try:
        import schedule
        import time
    except ImportError:
        logger.error("'schedule' package required. Install with: pip install schedule")
        sys.exit(1)

    scheduler_config = config.get("scheduler", {})
    run_at = scheduler_config.get("run_at", "09:00")

    logger.info("Scheduling job search to run daily at %s", run_at)

    schedule.every().day.at(run_at).do(run_search, config=config, profile=profile)

    # Also run immediately on first start
    run_search(config, profile)

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Job Search AI Agent - Find and track job opportunities automatically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py search                    # Search for new jobs
  python main.py search --apply            # Search and prepare applications
  python main.py search --min-score 0.8    # Only apply to 80%+ matches
  python main.py stats                     # Show statistics
  python main.py schedule                  # Run on daily schedule
        """,
    )

    parser.add_argument(
        "command",
        choices=["search", "stats", "schedule"],
        help="Command to run",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--profile",
        default="data/profile.yaml",
        help="Path to profile file (default: data/profile.yaml)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Auto-prepare applications for top matches",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.6,
        help="Minimum match score for auto-apply (0.0-1.0, default: 0.6)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load .env file
    load_dotenv()

    # Change to script directory for relative paths
    os.chdir(Path(__file__).parent)

    config = load_config(args.config)
    profile = load_profile(args.profile)

    if args.command == "search":
        run_search(config, profile, auto_apply=args.apply, min_score=args.min_score)
    elif args.command == "stats":
        show_stats(config)
    elif args.command == "schedule":
        run_scheduled(config, profile)


if __name__ == "__main__":
    main()
