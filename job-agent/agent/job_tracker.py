"""
Job Tracker Module - Uses only Python standard library.
Tracks seen/applied jobs and prevents duplicates.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from .job_searcher import Job

logger = logging.getLogger(__name__)


class JobTracker:
    """Tracks job applications and prevents duplicates."""

    def __init__(self, config: dict):
        storage = config.get("storage", {})
        self.jobs_file = Path(storage.get("jobs_file", "data/tracked_jobs.json"))
        self.applications_file = Path(storage.get("applications_file", "data/applications.json"))

        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self.applications_file.parent.mkdir(parents=True, exist_ok=True)

        self.tracked_jobs = self._load_json(self.jobs_file)
        self.applications = self._load_json(self.applications_file)

    @staticmethod
    def _load_json(filepath: Path) -> dict:
        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load %s: %s", filepath, e)
        return {}

    def _save_json(self, filepath: Path, data: dict):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def is_seen(self, job: Job) -> bool:
        return job.id in self.tracked_jobs

    def is_applied(self, job: Job) -> bool:
        return job.id in self.applications

    def mark_seen(self, job: Job):
        if job.id not in self.tracked_jobs:
            self.tracked_jobs[job.id] = {
                **job.to_dict(),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "status": "new",
            }
            self._save_json(self.jobs_file, self.tracked_jobs)

    def mark_applied(self, job: Job, method: str = "manual"):
        self.applications[job.id] = {
            **job.to_dict(),
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "status": "applied",
        }
        self._save_json(self.applications_file, self.applications)
        if job.id in self.tracked_jobs:
            self.tracked_jobs[job.id]["status"] = "applied"
            self._save_json(self.jobs_file, self.tracked_jobs)
        logger.info("Marked as applied: %s", job)

    def get_new_jobs(self, jobs: List[Job]) -> List[Job]:
        new_jobs = [j for j in jobs if not self.is_seen(j)]
        logger.info("%d new jobs out of %d total", len(new_jobs), len(jobs))
        return new_jobs

    def get_stats(self) -> dict:
        statuses = {}
        for job_data in self.tracked_jobs.values():
            status = job_data.get("status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        return {
            "total_seen": len(self.tracked_jobs),
            "total_applied": len(self.applications),
            "by_status": statuses,
        }
