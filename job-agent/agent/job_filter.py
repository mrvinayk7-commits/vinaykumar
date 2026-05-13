"""
Job Filter Module
Filters jobs based on user preferences, blacklists, and relevance criteria.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from .job_searcher import Job

logger = logging.getLogger(__name__)


class JobFilter:
    """Filters jobs based on user profile and preferences."""

    def __init__(self, profile: dict, search_config: dict):
        self.profile = profile
        self.search_config = search_config
        self.preferences = profile.get("preferences", {})

        # Build filter criteria
        self.blacklist_keywords = [
            kw.lower() for kw in self.preferences.get("blacklist_keywords", [])
        ]
        self.blacklist_companies = [
            c.lower() for c in self.preferences.get("blacklist_companies", [])
        ]
        self.max_age_hours = search_config.get("max_age_hours", 24)
        self.experience_level = search_config.get("experience_level", "any")
        self.job_type = search_config.get("job_type", "any")

    def filter_jobs(self, jobs: list[Job]) -> list[Job]:
        """Apply all filters and return matching jobs."""
        original_count = len(jobs)
        filtered = jobs

        # Apply each filter in sequence
        filtered = self._filter_blacklisted_companies(filtered)
        filtered = self._filter_blacklisted_keywords(filtered)
        filtered = self._filter_by_recency(filtered)
        filtered = self._filter_by_experience(filtered)
        filtered = self._filter_by_job_type(filtered)

        logger.info(
            "Filtered %d -> %d jobs (%d removed)",
            original_count,
            len(filtered),
            original_count - len(filtered),
        )
        return filtered

    def _filter_blacklisted_companies(self, jobs: list[Job]) -> list[Job]:
        """Remove jobs from blacklisted companies."""
        if not self.blacklist_companies:
            return jobs

        result = []
        for job in jobs:
            company_lower = job.company.lower()
            if not any(bc in company_lower for bc in self.blacklist_companies):
                result.append(job)
            else:
                logger.debug("Filtered out (blacklisted company): %s", job)

        return result

    def _filter_blacklisted_keywords(self, jobs: list[Job]) -> list[Job]:
        """Remove jobs containing blacklisted keywords."""
        if not self.blacklist_keywords:
            return jobs

        result = []
        for job in jobs:
            text = f"{job.title} {job.description}".lower()
            if not any(bk in text for bk in self.blacklist_keywords):
                result.append(job)
            else:
                logger.debug("Filtered out (blacklisted keyword): %s", job)

        return result

    def _filter_by_recency(self, jobs: list[Job]) -> list[Job]:
        """Only keep jobs posted within the configured time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)

        result = []
        for job in jobs:
            if job.posted_at and job.posted_at >= cutoff:
                result.append(job)
            elif job.posted_at is None:
                # Keep jobs with unknown post date (they passed API recency filters)
                result.append(job)
            else:
                logger.debug("Filtered out (too old): %s", job)

        return result

    def _filter_by_experience(self, jobs: list[Job]) -> list[Job]:
        """Filter by experience level if specified."""
        if self.experience_level == "any":
            return jobs

        level_keywords = {
            "entry": ["entry", "junior", "fresher", "graduate", "0-2 years", "0-1 years"],
            "mid": ["mid", "2-5 years", "3-5 years", "2+ years", "3+ years"],
            "senior": ["senior", "lead", "principal", "5+ years", "7+ years", "staff"],
        }

        target_keywords = level_keywords.get(self.experience_level, [])
        if not target_keywords:
            return jobs

        result = []
        for job in jobs:
            text = f"{job.title} {job.description}".lower()
            # Include if it matches the desired level OR has no clear level indicator
            matches_level = any(kw in text for kw in target_keywords)
            has_any_level = any(
                kw in text
                for kwlist in level_keywords.values()
                for kw in kwlist
            )

            if matches_level or not has_any_level:
                result.append(job)

        return result

    def _filter_by_job_type(self, jobs: list[Job]) -> list[Job]:
        """Filter by job type (full-time, part-time, etc.)."""
        if self.job_type == "any":
            return jobs

        type_keywords = {
            "full-time": ["full-time", "full time", "permanent"],
            "part-time": ["part-time", "part time"],
            "contract": ["contract", "freelance", "consulting"],
            "internship": ["intern", "internship", "trainee"],
        }

        target_keywords = type_keywords.get(self.job_type, [])
        if not target_keywords:
            return jobs

        result = []
        for job in jobs:
            text = f"{job.title} {job.description} {job.job_type or ''}".lower()
            matches_type = any(kw in text for kw in target_keywords)
            has_any_type = any(
                kw in text
                for kwlist in type_keywords.values()
                for kw in kwlist
            )

            if matches_type or not has_any_type:
                result.append(job)

        return result
