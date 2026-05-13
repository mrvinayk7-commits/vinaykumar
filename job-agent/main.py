#!/usr/bin/env python3
"""
Job Search AI Agent - Zero dependencies, uses only Python standard library.

Searches Google Jobs, LinkedIn, and Indeed for jobs posted in the last 24 hours,
filters and scores them against your profile, and tracks applications.

Usage:
    python3 main.py search
    python3 main.py search --apply
    python3 main.py stats
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from agent.job_searcher import JobSearcher
from agent.job_filter import JobFilter
from agent.resume_matcher import ResumeMatcher
from agent.job_tracker import JobTracker
from agent.notifier import Notifier
from agent.report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("job-agent")


def load_env(env_path: str = ".env"):
    """Load .env file into os.environ (no dependency needed)."""
    path = Path(env_path)
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def load_json_file(filepath: str, label: str) -> dict:
    """Load a JSON config file."""
    path = Path(filepath)
    if not path.exists():
        logger.error("%s not found: %s", label, filepath)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def run_search(config: dict, profile: dict, auto_apply: bool = False, min_score: float = 0.6):
    """Run a single job search cycle."""
    logger.info("Starting job search...")

    # 1. Search
    searcher = JobSearcher(config)
    all_jobs = searcher.search_all()

    if not all_jobs:
        logger.info("No jobs found. Check your API keys and search criteria.")
        print("\n  No jobs found. Make sure your API keys are valid.")
        print("  Test your SerpAPI key: https://serpapi.com/account")
        print("  Test your RapidAPI key: https://rapidapi.com/dashboard\n")
        return

    # 2. Filter
    job_filter = JobFilter(profile, config.get("search", {}))
    filtered_jobs = job_filter.filter_jobs(all_jobs)

    # 3. Track & deduplicate
    tracker = JobTracker(config)
    new_jobs = tracker.get_new_jobs(filtered_jobs)
    for job in new_jobs:
        tracker.mark_seen(job)

    # 4. Score & rank
    matcher = ResumeMatcher(profile, config)
    ranked_jobs = matcher.rank_jobs(new_jobs)

    # 5. Auto-apply
    if auto_apply:
        top = [(j, s) for j, s in ranked_jobs if s >= min_score]
        logger.info("Auto-apply: %d jobs above %.0f%% threshold", len(top), min_score * 100)
        for job, score in top:
            if not tracker.is_applied(job):
                tracker.mark_applied(job, method="agent")
                logger.info("Prepared application: %s @ %s (%.0f%%)", job.title, job.company, score * 100)

    # 6. Notify
    notifier = Notifier(config)
    stats = tracker.get_stats()
    notifier.notify(ranked_jobs, stats)

    # 7. Generate HTML report with clickable "Apply Now" links
    report = ReportGenerator()
    report_path = report.generate_and_open(ranked_jobs, stats)
    print(f"\n  HTML Report saved: {report_path}")
    print(f"  Open 'reports/latest_report.html' in your browser to see all jobs with Apply links!\n")

    logger.info("Search complete. Found %d new jobs.", len(new_jobs))


def show_stats(config: dict):
    """Display tracking statistics."""
    tracker = JobTracker(config)
    stats = tracker.get_stats()
    print(f"\n  Job Search Agent Statistics")
    print(f"  Total jobs seen:  {stats['total_seen']}")
    print(f"  Total applied:    {stats['total_applied']}")
    print(f"  By Status:")
    for status, count in stats.get("by_status", {}).items():
        print(f"    {status}: {count}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Job Search AI Agent")
    parser.add_argument("command", choices=["search", "stats"], help="Command to run")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--profile", default="data/profile.json", help="Profile file path")
    parser.add_argument("--apply", action="store_true", help="Auto-prepare applications for top matches")
    parser.add_argument("--min-score", type=float, default=0.6, help="Min match score for auto-apply (0.0-1.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Change to script directory
    os.chdir(Path(__file__).parent)

    # Load env
    load_env()

    config = load_json_file(args.config, "Config")
    profile = load_json_file(args.profile, "Profile")

    if args.command == "search":
        run_search(config, profile, auto_apply=args.apply, min_score=args.min_score)
    elif args.command == "stats":
        show_stats(config)


if __name__ == "__main__":
    main()
