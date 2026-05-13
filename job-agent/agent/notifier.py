"""
Notifier Module
Sends notifications about new job matches via email and/or console.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

from .job_searcher import Job

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Display job results in the terminal using rich formatting."""

    def notify(self, ranked_jobs: list[tuple[Job, float]], stats: dict) -> None:
        """Print job results to console."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel

            console = Console()

            # Header
            console.print(
                Panel(
                    f"[bold green]Job Search Agent Report[/bold green]\n"
                    f"[dim]{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}[/dim]",
                    border_style="green",
                )
            )

            # Stats
            console.print(f"\n[bold]Stats:[/bold] "
                         f"Total seen: {stats.get('total_seen', 0)} | "
                         f"Applied: {stats.get('total_applied', 0)}")

            if not ranked_jobs:
                console.print("\n[yellow]No new jobs found matching your criteria.[/yellow]")
                return

            # Jobs table
            table = Table(title=f"Found {len(ranked_jobs)} New Jobs", show_lines=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Score", style="bold", width=6)
            table.add_column("Title", style="cyan", min_width=20)
            table.add_column("Company", style="green", min_width=15)
            table.add_column("Location", min_width=12)
            table.add_column("Source", style="dim", width=10)
            table.add_column("URL", style="blue", min_width=20)

            for i, (job, score) in enumerate(ranked_jobs, 1):
                score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
                table.add_row(
                    str(i),
                    f"[{score_color}]{score:.0%}[/{score_color}]",
                    job.title[:40],
                    job.company[:20],
                    job.location[:15],
                    job.source,
                    job.url[:50] if job.url else "N/A",
                )

            console.print(table)
            console.print()

        except ImportError:
            # Fallback without rich
            self._plain_notify(ranked_jobs, stats)

    @staticmethod
    def _plain_notify(ranked_jobs: list[tuple[Job, float]], stats: dict) -> None:
        """Plain text fallback when rich is not available."""
        print("\n" + "=" * 60)
        print("JOB SEARCH AGENT REPORT")
        print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Stats: Seen={stats.get('total_seen', 0)}, Applied={stats.get('total_applied', 0)}")
        print("=" * 60)

        if not ranked_jobs:
            print("No new jobs found matching your criteria.")
            return

        print(f"\nFound {len(ranked_jobs)} new jobs:\n")
        for i, (job, score) in enumerate(ranked_jobs, 1):
            print(f"{i}. [{score:.0%}] {job.title} @ {job.company}")
            print(f"   Location: {job.location} | Source: {job.source}")
            print(f"   URL: {job.url}")
            print()


class EmailNotifier:
    """Send job results via email."""

    def __init__(self, config: dict):
        email_config = config.get("notifications", {}).get("email", {})
        self.enabled = email_config.get("enabled", False)
        self.smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = email_config.get("smtp_port", 587)
        self.sender = os.getenv(
            "SMTP_SENDER_EMAIL", email_config.get("sender_email", "")
        )
        self.password = os.getenv(
            "SMTP_SENDER_PASSWORD", email_config.get("sender_password", "")
        )
        self.recipient = os.getenv(
            "SMTP_RECIPIENT_EMAIL", email_config.get("recipient_email", "")
        )

    def notify(self, ranked_jobs: list[tuple[Job, float]], stats: dict) -> None:
        """Send email notification with job results."""
        if not self.enabled:
            return

        if not all([self.sender, self.password, self.recipient]):
            logger.warning("Email notification enabled but credentials not configured")
            return

        if not ranked_jobs:
            logger.info("No new jobs to notify about via email")
            return

        try:
            html_body = self._build_html(ranked_jobs, stats)
            self._send_email(
                subject=f"Job Agent: {len(ranked_jobs)} new jobs found",
                html_body=html_body,
            )
            logger.info("Email notification sent to %s", self.recipient)
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)

    def _build_html(self, ranked_jobs: list[tuple[Job, float]], stats: dict) -> str:
        """Build HTML email body."""
        rows = ""
        for i, (job, score) in enumerate(ranked_jobs, 1):
            color = "#22c55e" if score >= 0.7 else "#eab308" if score >= 0.4 else "#ef4444"
            rows += f"""
            <tr>
                <td>{i}</td>
                <td style="color:{color};font-weight:bold">{score:.0%}</td>
                <td><a href="{job.url}">{job.title}</a></td>
                <td>{job.company}</td>
                <td>{job.location}</td>
                <td>{job.source}</td>
            </tr>"""

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Job Search Agent Report</h2>
            <p>Found <strong>{len(ranked_jobs)}</strong> new jobs matching your criteria.</p>
            <p>Total tracked: {stats.get('total_seen', 0)} | Applied: {stats.get('total_applied', 0)}</p>
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%;">
                <tr style="background:#f3f4f6;">
                    <th>#</th><th>Match</th><th>Title</th><th>Company</th><th>Location</th><th>Source</th>
                </tr>
                {rows}
            </table>
            <p style="color:#6b7280;font-size:12px;margin-top:20px;">
                Sent by Job Search Agent at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </body>
        </html>"""

    def _send_email(self, subject: str, html_body: str) -> None:
        """Send an email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.recipient, msg.as_string())


class Notifier:
    """Main notifier that dispatches to all configured channels."""

    def __init__(self, config: dict):
        self.config = config
        self.channels = []

        notif_config = config.get("notifications", {})

        if notif_config.get("console", {}).get("enabled", True):
            self.channels.append(ConsoleNotifier())

        if notif_config.get("email", {}).get("enabled", False):
            self.channels.append(EmailNotifier(config))

    def notify(self, ranked_jobs: list[tuple[Job, float]], stats: dict) -> None:
        """Send notifications through all configured channels."""
        for channel in self.channels:
            try:
                channel.notify(ranked_jobs, stats)
            except Exception as e:
                logger.error(
                    "Notification channel %s failed: %s",
                    type(channel).__name__,
                    e,
                )
