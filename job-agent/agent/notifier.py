"""
Notifier Module - Uses only Python standard library.
Prints job results to console in a formatted table.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import List, Tuple

from .job_searcher import Job

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Display job results in the terminal."""

    def notify(self, ranked_jobs: List[Tuple[Job, float]], stats: dict):
        print()
        print("=" * 80)
        print("  JOB SEARCH AGENT REPORT")
        print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Total seen: {stats.get('total_seen', 0)} | Applied: {stats.get('total_applied', 0)}")
        print("=" * 80)

        if not ranked_jobs:
            print("\n  No new jobs found matching your criteria.\n")
            return

        print(f"\n  Found {len(ranked_jobs)} new job(s):\n")
        print(f"  {'#':<4} {'Score':<7} {'Title':<35} {'Company':<20} {'Location':<15} {'Source':<10}")
        print("  " + "-" * 91)

        for i, (job, score) in enumerate(ranked_jobs, 1):
            score_str = f"{score:.0%}"
            print(f"  {i:<4} {score_str:<7} {job.title[:33]:<35} {job.company[:18]:<20} {job.location[:13]:<15} {job.source:<10}")

        print()
        print("  Job URLs:")
        for i, (job, score) in enumerate(ranked_jobs, 1):
            if job.url:
                print(f"  {i}. {job.url}")
        print()


class EmailNotifier:
    """Send job results via email."""

    def __init__(self, config: dict):
        email_config = config.get("notifications", {}).get("email", {})
        self.enabled = email_config.get("enabled", False)
        self.smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = email_config.get("smtp_port", 587)
        self.sender = os.getenv("SMTP_SENDER_EMAIL", email_config.get("sender_email", ""))
        self.password = os.getenv("SMTP_SENDER_PASSWORD", email_config.get("sender_password", ""))
        self.recipient = os.getenv("SMTP_RECIPIENT_EMAIL", email_config.get("recipient_email", ""))

    def notify(self, ranked_jobs: List[Tuple[Job, float]], stats: dict):
        if not self.enabled or not ranked_jobs:
            return
        if not all([self.sender, self.password, self.recipient]):
            logger.warning("Email not configured properly")
            return

        try:
            rows = ""
            for i, (job, score) in enumerate(ranked_jobs, 1):
                rows += f"<tr><td>{i}</td><td>{score:.0%}</td><td><a href='{job.url}'>{job.title}</a></td><td>{job.company}</td><td>{job.location}</td></tr>"

            html = f"""<html><body>
            <h2>Job Agent: {len(ranked_jobs)} new jobs</h2>
            <table border='1' cellpadding='5'><tr><th>#</th><th>Match</th><th>Title</th><th>Company</th><th>Location</th></tr>{rows}</table>
            </body></html>"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Job Agent: {len(ranked_jobs)} new jobs found"
            msg["From"] = self.sender
            msg["To"] = self.recipient
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipient, msg.as_string())
            logger.info("Email sent to %s", self.recipient)
        except Exception as e:
            logger.error("Email failed: %s", e)


class Notifier:
    """Main notifier that dispatches to all channels."""

    def __init__(self, config: dict):
        self.channels = []
        notif = config.get("notifications", {})
        if notif.get("console", {}).get("enabled", True):
            self.channels.append(ConsoleNotifier())
        if notif.get("email", {}).get("enabled", False):
            self.channels.append(EmailNotifier(config))

    def notify(self, ranked_jobs: List[Tuple[Job, float]], stats: dict):
        for channel in self.channels:
            try:
                channel.notify(ranked_jobs, stats)
            except Exception as e:
                logger.error("Notification failed: %s", e)
