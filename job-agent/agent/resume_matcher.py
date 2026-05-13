"""
Resume Matcher Module - Uses only Python standard library.
Scores jobs against user profile using keyword matching.
"""

import logging
from typing import List, Tuple

from .job_searcher import Job

logger = logging.getLogger(__name__)


class ResumeMatcher:
    """Matches jobs against the user's profile using keyword matching."""

    def __init__(self, profile: dict, config: dict):
        self.profile = profile
        self.config = config

        # Collect all skills
        skills_section = profile.get("skills", {})
        self.all_skills = []
        for category in skills_section.values():
            if isinstance(category, list):
                self.all_skills.extend([s.lower() for s in category])

    def score_job(self, job: Job) -> float:
        """Score a job from 0.0 to 1.0 based on skill keyword matches."""
        if not self.all_skills:
            return 0.5

        text = f"{job.title} {job.description}".lower()
        matches = sum(1 for skill in self.all_skills if skill.lower() in text)
        score = min(matches / max(len(self.all_skills) * 0.3, 1), 1.0)
        return round(score, 2)

    def rank_jobs(self, jobs: List[Job]) -> List[Tuple[Job, float]]:
        """Score and rank all jobs by relevance."""
        scored = [(job, self.score_job(job)) for job in jobs]
        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info("Ranked %d jobs by relevance", len(scored))
        return scored
