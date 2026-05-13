"""
Job Filter Module - Uses only Python standard library.
Filters jobs based on user preferences, blacklists, and relevance criteria.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from .job_searcher import Job

logger = logging.getLogger(__name__)


class JobFilter:
    """Filters jobs based on user profile and preferences."""

    def __init__(self, profile: dict, search_config: dict):
        self.profile = profile
        self.search_config = search_config
        self.preferences = profile.get("preferences", {})

        self.blacklist_keywords = [kw.lower() for kw in self.preferences.get("blacklist_keywords", [])]
        self.blacklist_companies = [c.lower() for c in self.preferences.get("blacklist_companies", [])]
        self.max_age_hours = search_config.get("max_age_hours", 24)
        self.experience_level = search_config.get("experience_level", "any")
        self.job_type = search_config.get("job_type", "any")

    def filter_jobs(self, jobs: List[Job]) -> List[Job]:
        original_count = len(jobs)
        filtered = jobs
        filtered = self._filter_blacklisted_companies(filtered)
        filtered = self._filter_blacklisted_keywords(filtered)
        filtered = self._filter_by_recency(filtered)
        filtered = self._filter_by_experience(filtered)
        filtered = self._filter_by_job_type(filtered)
        logger.info("Filtered %d -> %d jobs (%d removed)", original_count, len(filtered), original_count - len(filtered))
        return filtered

    def _filter_blacklisted_companies(self, jobs: List[Job]) -> List[Job]:
        if not self.blacklist_companies:
            return jobs
        return [j for j in jobs if not any(bc in j.company.lower() for bc in self.blacklist_companies)]

    def _filter_blacklisted_keywords(self, jobs: List[Job]) -> List[Job]:
        if not self.blacklist_keywords:
            return jobs
        return [j for j in jobs if not any(bk in f"{j.title} {j.description}".lower() for bk in self.blacklist_keywords)]

    def _filter_by_recency(self, jobs: List[Job]) -> List[Job]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)
        return [j for j in jobs if j.posted_at is None or j.posted_at >= cutoff]

    def _filter_by_experience(self, jobs: List[Job]) -> List[Job]:
        if self.experience_level == "any":
            return jobs
        level_keywords = {
            "entry": ["entry", "junior", "fresher", "graduate", "0-2 years"],
            "mid": ["mid", "2-5 years", "3-5 years", "2+ years", "3+ years"],
            "senior": ["senior", "lead", "principal", "5+ years", "staff"],
        }
        target = level_keywords.get(self.experience_level, [])
        if not target:
            return jobs

        result = []
        for job in jobs:
            text = f"{job.title} {job.description}".lower()
            matches = any(kw in text for kw in target)
            has_any = any(kw in text for kwlist in level_keywords.values() for kw in kwlist)
            if matches or not has_any:
                result.append(job)
        return result

    def _filter_by_job_type(self, jobs: List[Job]) -> List[Job]:
        if self.job_type == "any":
            return jobs
        type_keywords = {
            "full-time": ["full-time", "full time", "permanent"],
            "part-time": ["part-time", "part time"],
            "contract": ["contract", "freelance"],
            "internship": ["intern", "internship"],
        }
        target = type_keywords.get(self.job_type, [])
        if not target:
            return jobs

        result = []
        for job in jobs:
            text = f"{job.title} {job.description} {job.job_type or ''}".lower()
            matches = any(kw in text for kw in target)
            has_any = any(kw in text for kwlist in type_keywords.values() for kw in kwlist)
            if matches or not has_any:
                result.append(job)
        return result
