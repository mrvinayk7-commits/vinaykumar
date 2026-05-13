# Job Search AI Agent

An intelligent job search agent that automatically finds job postings from the last 24 hours across multiple platforms (Google Jobs, LinkedIn, Indeed), filters them based on your profile and preferences, scores them by relevance, and notifies you of the best matches.

## Features

- **Multi-source job search** - Searches Google Jobs, LinkedIn, and Indeed simultaneously
- **Smart filtering** - Filters by recency (last 24h), keywords, location, experience level, job type
- **AI-powered matching** - Scores jobs against your profile using keyword matching + optional OpenAI
- **Cover letter generation** - Automatically generates tailored cover letters (requires OpenAI API)
- **Duplicate tracking** - Never shows you the same job twice
- **Application tracking** - Keeps track of all jobs you've seen, applied to, or skipped
- **Email notifications** - Get daily email summaries of new matching jobs
- **Scheduled runs** - Run automatically every 24 hours

## Quick Start

### 1. Install dependencies

```bash
cd job-agent
pip install -r requirements.txt
```

### 2. Configure API keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add at least one of these API keys:

| Key | Source | Free Tier |
|-----|--------|-----------|
| `SERPAPI_KEY` | [serpapi.com](https://serpapi.com) | 100 searches/month |
| `RAPIDAPI_KEY` | [rapidapi.com](https://rapidapi.com) | Varies by API |
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | Pay-as-you-go |

### 3. Set up your profile

Edit `data/profile.yaml` with your personal details, skills, experience, and preferences. This is used for job matching and scoring.

### 4. Configure search settings

Edit `config.yaml` to set your:
- Search keywords (job titles you're looking for)
- Preferred locations
- Experience level
- Job type preferences
- Notification settings

### 5. Run the agent

```bash
# Search for new jobs
python main.py search

# Search and auto-prepare applications for top matches
python main.py search --apply

# Only apply to jobs with 80%+ match score
python main.py search --apply --min-score 0.8

# View statistics
python main.py stats

# Run on a daily schedule
python main.py schedule
```

## Project Structure

```
job-agent/
  main.py                  # CLI entry point
  config.yaml              # Search and notification settings
  requirements.txt         # Python dependencies
  .env.example             # API key template
  agent/
    __init__.py
    job_searcher.py         # Multi-source job search
    job_filter.py           # Smart job filtering
    resume_matcher.py       # AI-powered job-profile matching
    job_tracker.py          # Application and history tracking
    notifier.py             # Console and email notifications
  data/
    profile.yaml            # Your profile and preferences
    tracked_jobs.json       # Auto-generated: seen jobs
    applications.json       # Auto-generated: application history
```

## How It Works

1. **Search** - Queries multiple job board APIs for recent postings matching your keywords and locations
2. **Filter** - Removes jobs that don't match your preferences (blacklisted companies, wrong experience level, etc.)
3. **Deduplicate** - Checks against previously seen jobs to only show new listings
4. **Score** - Matches each job against your skills and experience (keyword-based + optional AI scoring)
5. **Rank** - Sorts jobs by relevance score so the best matches appear first
6. **Notify** - Displays results in a formatted table and optionally sends email notifications
7. **Track** - Saves all seen and applied jobs for future reference

## Automate with Cron

To run the agent automatically every day at 9 AM:

```bash
# Edit crontab
crontab -e

# Add this line (adjust paths as needed)
0 9 * * * cd /path/to/job-agent && /path/to/python main.py search --apply >> /var/log/job-agent.log 2>&1
```

## Important Notes

- **LinkedIn ToS**: This agent uses public APIs and does not automate LinkedIn's UI or bypass any restrictions. Direct LinkedIn automation (like browser-based auto-apply) violates their Terms of Service.
- **API costs**: SerpAPI offers 100 free searches/month. RapidAPI pricing varies. OpenAI charges per token.
- **Data privacy**: Your profile data stays local. API keys should never be committed to git.

## License

MIT
