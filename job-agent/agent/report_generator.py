"""
Report Generator Module
Creates an HTML report file with all found jobs, clickable links, and match scores.
Opens automatically in the browser after generation.
"""

import json
import logging
import os
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from .job_searcher import Job

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML report files with job listings."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, ranked_jobs: List[Tuple[Job, float]], stats: dict) -> str:
        """Generate an HTML report and return the file path."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        filename = f"jobs_report_{timestamp}.html"
        filepath = self.output_dir / filename

        # Also generate a "latest" report that always has the most recent results
        latest_path = self.output_dir / "latest_report.html"

        html = self._build_html(ranked_jobs, stats)

        # Write both files
        for path in [filepath, latest_path]:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

        logger.info("HTML report saved to: %s", filepath)
        return str(filepath)

    def generate_and_open(self, ranked_jobs: List[Tuple[Job, float]], stats: dict) -> str:
        """Generate report and open it in the default browser."""
        filepath = self.generate(ranked_jobs, stats)
        try:
            abs_path = os.path.abspath(filepath)
            webbrowser.open(f"file://{abs_path}")
            logger.info("Opened report in browser")
        except Exception as e:
            logger.warning("Could not open browser: %s", e)
            print(f"\n  Report saved at: {filepath}")
            print(f"  Open this file in your browser to see the results.\n")
        return filepath

    def _build_html(self, ranked_jobs: List[Tuple[Job, float]], stats: dict) -> str:
        """Build the HTML report content."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Build job rows
        rows = ""
        for i, (job, score) in enumerate(ranked_jobs, 1):
            score_pct = int(score * 100)
            if score_pct >= 70:
                badge_color = "#22c55e"
                badge_bg = "#dcfce7"
            elif score_pct >= 40:
                badge_color = "#ca8a04"
                badge_bg = "#fef9c3"
            else:
                badge_color = "#dc2626"
                badge_bg = "#fee2e2"

            apply_link = job.url if job.url else "#"
            rows += f"""
            <tr>
                <td>{i}</td>
                <td>
                    <span style="background:{badge_bg}; color:{badge_color}; padding:2px 10px; border-radius:12px; font-weight:bold;">
                        {score_pct}%
                    </span>
                </td>
                <td><strong>{job.title}</strong></td>
                <td>{job.company}</td>
                <td>{job.location}</td>
                <td>{job.source}</td>
                <td>
                    <a href="{apply_link}" target="_blank" 
                       style="background:#2563eb; color:white; padding:6px 16px; border-radius:6px; text-decoration:none; font-size:13px;">
                        Apply Now
                    </a>
                </td>
            </tr>"""

        if not ranked_jobs:
            rows = """
            <tr>
                <td colspan="7" style="text-align:center; padding:40px; color:#6b7280;">
                    No new jobs found matching your criteria. Try again later or adjust your search keywords.
                </td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Search Report - {now}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f4f6; color: #1f2937; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .stats {{ display: flex; gap: 16px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; flex: 1; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .stat-card .number {{ font-size: 28px; font-weight: bold; color: #1e40af; }}
        .stat-card .label {{ font-size: 13px; color: #6b7280; margin-top: 4px; }}
        table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-collapse: collapse; }}
        th {{ background: #f9fafb; padding: 14px 16px; text-align: left; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb; }}
        td {{ padding: 14px 16px; border-bottom: 1px solid #f3f4f6; font-size: 14px; }}
        tr:hover {{ background: #f9fafb; }}
        .footer {{ text-align: center; padding: 20px; color: #9ca3af; font-size: 12px; margin-top: 20px; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Job Search Agent Report</h1>
            <p>Generated on {now} | Jobs from the last 24 hours</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number">{len(ranked_jobs)}</div>
                <div class="label">New Jobs Found</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('total_seen', 0)}</div>
                <div class="label">Total Jobs Tracked</div>
            </div>
            <div class="stat-card">
                <div class="number">{stats.get('total_applied', 0)}</div>
                <div class="label">Applications Sent</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Match</th>
                    <th>Job Title</th>
                    <th>Company</th>
                    <th>Location</th>
                    <th>Source</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <div class="footer">
            <p>Generated by Job Search AI Agent | Click "Apply Now" to open the job posting</p>
        </div>
    </div>
</body>
</html>"""
