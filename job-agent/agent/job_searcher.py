"""
Job Searcher Module
Searches for jobs from multiple sources including Google Jobs (via SerpAPI),
LinkedIn Jobs (via RapidAPI), and other job boards.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class Job:
    """Represents a single job listing."""

    def __init__(
        self,
        title: str,
        company: str,
        location: str,
        description: str,
        url: str,
        source: str,
        posted_at: Optional[datetime] = None,
        salary: Optional[str] = None,
        job_type: Optional[str] = None,
        experience_level: Optional[str] = None,
    ):
        self.id = f"{source}:{company}:{title}".lower().replace(" ", "-")
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.url = url
        self.source = source
        self.posted_at = posted_at or datetime.now(timezone.utc)
        self.salary = salary
        self.job_type = job_type
        self.experience_level = experience_level
        self.discovered_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description[:500],  # Truncate for storage
            "url": self.url,
            "source": self.source,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "salary": self.salary,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "discovered_at": self.discovered_at.isoformat(),
        }

    def __repr__(self):
        return f"Job({self.title} @ {self.company} [{self.source}])"


class GoogleJobsSearcher:
    """Search jobs using Google Jobs via SerpAPI."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(
        self,
        keywords: list[str],
        locations: list[str],
        max_age_hours: int = 24,
    ) -> list[Job]:
        """Search Google Jobs for matching positions."""
        jobs = []

        if not self.api_key:
            logger.warning("SerpAPI key not set, skipping Google Jobs search")
            return jobs

        for keyword in keywords:
            for location in locations:
                try:
                    results = self._search_query(keyword, location, max_age_hours)
                    jobs.extend(results)
                except Exception as e:
                    logger.error(
                        "Google Jobs search failed for '%s' in '%s': %s",
                        keyword,
                        location,
                        e,
                    )

        return jobs

    def _search_query(
        self, keyword: str, location: str, max_age_hours: int
    ) -> list[Job]:
        """Execute a single search query."""
        params = {
            "engine": "google_jobs",
            "q": keyword,
            "location": location,
            "api_key": self.api_key,
            "chips": f"date_posted:today",  # Last 24 hours
        }

        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for result in data.get("jobs_results", []):
            job = Job(
                title=result.get("title", "Unknown"),
                company=result.get("company_name", "Unknown"),
                location=result.get("location", location),
                description=result.get("description", ""),
                url=result.get("share_link", result.get("related_links", [{}])[0].get("link", "")),
                source="google_jobs",
                salary=result.get("salary", None),
                job_type=self._extract_job_type(result),
            )
            jobs.append(job)

        logger.info(
            "Found %d jobs for '%s' in '%s' via Google Jobs",
            len(jobs),
            keyword,
            location,
        )
        return jobs

    @staticmethod
    def _extract_job_type(result: dict) -> Optional[str]:
        """Extract job type from detected extensions."""
        extensions = result.get("detected_extensions", {})
        if extensions.get("work_from_home"):
            return "remote"
        schedule = extensions.get("schedule_type", "")
        return schedule if schedule else None


class LinkedInJobsSearcher:
    """Search jobs using LinkedIn Jobs API via RapidAPI."""

    BASE_URL = "https://linkedin-jobs-search.p.rapidapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(
        self,
        keywords: list[str],
        locations: list[str],
        max_age_hours: int = 24,
    ) -> list[Job]:
        """Search LinkedIn for matching positions."""
        jobs = []

        if not self.api_key:
            logger.warning("RapidAPI key not set, skipping LinkedIn search")
            return jobs

        for keyword in keywords:
            for location in locations:
                try:
                    results = self._search_query(keyword, location, max_age_hours)
                    jobs.extend(results)
                except Exception as e:
                    logger.error(
                        "LinkedIn search failed for '%s' in '%s': %s",
                        keyword,
                        location,
                        e,
                    )

        return jobs

    def _search_query(
        self, keyword: str, location: str, max_age_hours: int
    ) -> list[Job]:
        """Execute a single LinkedIn search query."""
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com",
            "Content-Type": "application/json",
        }

        payload = {
            "search_terms": keyword,
            "location": location,
            "page": "1",
            "fetch_full_text": "yes",
        }

        response = requests.post(
            f"{self.BASE_URL}/", headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        jobs = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for item in data if isinstance(data, list) else []:
            posted_date = self._parse_date(item.get("posted_date", ""))

            # Filter by recency
            if posted_date and posted_date < cutoff:
                continue

            job = Job(
                title=item.get("job_title", "Unknown"),
                company=item.get("company_name", "Unknown"),
                location=item.get("job_location", location),
                description=item.get("job_description", ""),
                url=item.get("job_url", ""),
                source="linkedin",
                posted_at=posted_date,
            )
            jobs.append(job)

        logger.info(
            "Found %d jobs for '%s' in '%s' via LinkedIn",
            len(jobs),
            keyword,
            location,
        )
        return jobs

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse a date string from LinkedIn."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


class IndeedSearcher:
    """Search jobs from Indeed via RapidAPI."""

    BASE_URL = "https://indeed12.p.rapidapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(
        self,
        keywords: list[str],
        locations: list[str],
        max_age_hours: int = 24,
    ) -> list[Job]:
        """Search Indeed for matching positions."""
        jobs = []

        if not self.api_key:
            logger.warning("RapidAPI key not set, skipping Indeed search")
            return jobs

        for keyword in keywords:
            for location in locations:
                try:
                    results = self._search_query(keyword, location)
                    jobs.extend(results)
                except Exception as e:
                    logger.error(
                        "Indeed search failed for '%s' in '%s': %s",
                        keyword,
                        location,
                        e,
                    )

        return jobs

    def _search_query(self, keyword: str, location: str) -> list[Job]:
        """Execute a single Indeed search query."""
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "indeed12.p.rapidapi.com",
        }

        params = {
            "query": keyword,
            "location": location,
            "page_id": "1",
            "locality": "in",  # India
            "fromage": "1",  # Last 1 day
            "sort": "date",
        }

        response = requests.get(
            f"{self.BASE_URL}/jobs/search",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        jobs = []
        for hit in data.get("hits", []):
            job = Job(
                title=hit.get("title", "Unknown"),
                company=hit.get("company_name", "Unknown"),
                location=hit.get("location", location),
                description=hit.get("description", ""),
                url=f"https://indeed.com/viewjob?jk={hit.get('id', '')}",
                source="indeed",
                salary=hit.get("salary", {}).get("text"),
            )
            jobs.append(job)

        logger.info(
            "Found %d jobs for '%s' in '%s' via Indeed",
            len(jobs),
            keyword,
            location,
        )
        return jobs


class JobSearcher:
    """Aggregates results from all job search sources."""

    def __init__(self, config: dict):
        self.config = config
        apis = config.get("apis", {})

        serpapi_key = os.getenv("SERPAPI_KEY", apis.get("serpapi_key", ""))
        rapidapi_key = os.getenv("RAPIDAPI_KEY", apis.get("rapidapi_key", ""))

        self.searchers = [
            GoogleJobsSearcher(serpapi_key),
            LinkedInJobsSearcher(rapidapi_key),
            IndeedSearcher(rapidapi_key),
        ]

    def search_all(self) -> list[Job]:
        """Search all configured job sources and return combined results."""
        search_config = self.config.get("search", {})
        keywords = search_config.get("keywords", ["software engineer"])
        locations = search_config.get("locations", ["Remote"])
        max_age_hours = search_config.get("max_age_hours", 24)

        all_jobs = []
        for searcher in self.searchers:
            try:
                jobs = searcher.search(keywords, locations, max_age_hours)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error("Searcher %s failed: %s", type(searcher).__name__, e)

        # Deduplicate by normalized title+company
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = (job.title.lower().strip(), job.company.lower().strip())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        logger.info(
            "Total: %d jobs found (%d unique) across all sources",
            len(all_jobs),
            len(unique_jobs),
        )
        return unique_jobs
