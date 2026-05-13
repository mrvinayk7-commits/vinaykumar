"""
Resume Matcher Module
Uses AI to match your profile/resume against job descriptions
and score relevance. Can also generate tailored cover letters.
"""

import logging
import os
from typing import Optional

from .job_searcher import Job

logger = logging.getLogger(__name__)


class ResumeMatcher:
    """Matches jobs against the user's profile using keyword matching and optional AI."""

    def __init__(self, profile: dict, config: dict):
        self.profile = profile
        self.config = config

        # Collect all skills from profile
        skills_section = profile.get("skills", {})
        self.all_skills = []
        for category in skills_section.values():
            if isinstance(category, list):
                self.all_skills.extend([s.lower() for s in category])

        # OpenAI setup (optional)
        self.openai_client = None
        api_key = os.getenv(
            "OPENAI_API_KEY", config.get("apis", {}).get("openai_api_key", "")
        )
        if api_key:
            try:
                from openai import OpenAI

                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized for AI-powered matching")
            except ImportError:
                logger.warning("openai package not installed, using keyword matching only")

    def score_job(self, job: Job) -> float:
        """
        Score a job from 0.0 to 1.0 based on how well it matches the profile.
        Uses keyword matching as the primary method, with optional AI scoring.
        """
        # Keyword-based scoring
        keyword_score = self._keyword_score(job)

        # If OpenAI is available, blend with AI score
        if self.openai_client:
            try:
                ai_score = self._ai_score(job)
                # Weighted blend: 40% keywords, 60% AI
                return 0.4 * keyword_score + 0.6 * ai_score
            except Exception as e:
                logger.warning("AI scoring failed, using keyword score: %s", e)

        return keyword_score

    def _keyword_score(self, job: Job) -> float:
        """Score based on skill keyword matches in the job description."""
        if not self.all_skills:
            return 0.5  # Neutral if no skills defined

        text = f"{job.title} {job.description}".lower()
        matches = sum(1 for skill in self.all_skills if skill in text)
        score = min(matches / max(len(self.all_skills) * 0.3, 1), 1.0)

        return score

    def _ai_score(self, job: Job) -> float:
        """Use OpenAI to score job-profile match."""
        if not self.openai_client:
            return 0.5

        profile_summary = self._build_profile_summary()
        job_summary = f"Title: {job.title}\nCompany: {job.company}\nDescription: {job.description[:1000]}"

        prompt = f"""Rate how well this job matches the candidate's profile on a scale of 0.0 to 1.0.
Consider skills match, experience level, and overall fit.
Return ONLY a decimal number between 0.0 and 1.0.

CANDIDATE PROFILE:
{profile_summary}

JOB POSTING:
{job_summary}

Score:"""

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )

        score_text = response.choices[0].message.content.strip()
        try:
            score = float(score_text)
            return max(0.0, min(1.0, score))
        except ValueError:
            logger.warning("Could not parse AI score: %s", score_text)
            return 0.5

    def generate_cover_letter(self, job: Job) -> Optional[str]:
        """Generate a tailored cover letter for a specific job using AI."""
        if not self.openai_client:
            logger.info("OpenAI not available, cannot generate cover letter")
            return None

        profile_summary = self._build_profile_summary()

        prompt = f"""Write a concise, professional cover letter for this job application.
Keep it under 250 words. Be specific about how the candidate's skills match the role.

CANDIDATE PROFILE:
{profile_summary}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Description: {job.description[:1500]}

Cover Letter:"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Failed to generate cover letter: %s", e)
            return None

    def _build_profile_summary(self) -> str:
        """Build a text summary of the user's profile."""
        parts = []

        name = self.profile.get("personal", {}).get("name", "Candidate")
        parts.append(f"Name: {name}")

        summary = self.profile.get("summary", "")
        if summary:
            parts.append(f"Summary: {summary.strip()}")

        skills = self.profile.get("skills", {})
        for category, skill_list in skills.items():
            if isinstance(skill_list, list):
                parts.append(f"{category}: {', '.join(skill_list)}")

        experience = self.profile.get("experience", [])
        for exp in experience:
            parts.append(
                f"Experience: {exp.get('title', '')} at {exp.get('company', '')} "
                f"({exp.get('start_date', '')} - {exp.get('end_date', '')})"
            )

        return "\n".join(parts)

    def rank_jobs(self, jobs: list[Job]) -> list[tuple[Job, float]]:
        """Score and rank all jobs by relevance. Returns (job, score) tuples."""
        scored = []
        for job in jobs:
            score = self.score_job(job)
            scored.append((job, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        logger.info("Ranked %d jobs by relevance", len(scored))
        return scored
