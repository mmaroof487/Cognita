"""
Email service for sending notifications.

Handles SMTP email sending with HTML templates and attachments.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Raised when email sending fails."""

    pass


class EmailClient:
    """SMTP email client."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
    ):
        """
        Initialize email client.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (usually 587 for TLS, 25 for plain)
            username: SMTP username
            password: SMTP password
            from_address: Sender email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
    ) -> dict:
        """
        Send email message.

        Args:
            to: Recipient email(s)
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body (takes precedence over body)
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients

        Returns:
            Send confirmation: {ok, message_id}

        Raises:
            EmailError: On SMTP failure
        """
        # Normalize recipients
        if isinstance(to, str):
            to = [to]

        all_recipients = to.copy()
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_address
            message["To"] = ", ".join(to)

            if cc:
                message["Cc"] = ", ".join(cc)

            # Add body parts
            if body:
                part1 = MIMEText(body, "plain")
                message.attach(part1)

            if html_body:
                part2 = MIMEText(html_body, "html")
                message.attach(part2)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.username, self.password)

                server.sendmail(
                    self.from_address,
                    all_recipients,
                    message.as_string(),
                )

            logger.info(f"Email sent to {', '.join(to)} with subject: {subject}")

            return {
                "ok": True,
                "to": to,
                "subject": subject,
                "message_id": message.get("Message-ID"),
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise EmailError(f"Authentication failed: {e}") from e

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise EmailError(f"SMTP error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailError(f"Unexpected error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def send_alert(
        self,
        to: str | list[str],
        title: str,
        message: str,
        severity: str = "info",
        details: Optional[dict] = None,
    ) -> dict:
        """
        Send alert-style email with formatted content.

        Args:
            to: Recipient email(s)
            title: Alert title
            message: Alert message
            severity: "info", "warning", "error", "critical"
            details: Additional details to include

        Returns:
            Send confirmation
        """
        # Build HTML body
        severity_colors = {
            "info": "#3498db",  # Blue
            "warning": "#f39c12",  # Orange
            "error": "#e74c3c",  # Red
            "critical": "#8b0000",  # Dark red
        }

        color = severity_colors.get(severity, "#3498db")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 5px solid {color}; padding: 20px; background: #f9f9f9;">
                <h2 style="margin-top: 0; color: {color};">🚀 {title}</h2>
                <p>{message}</p>
        """

        if details:
            html += "<h3>Details:</h3><ul>"
            for key, value in details.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul>"

        html += """
            </div>
        </body>
        </html>
        """

        subject = f"[{severity.upper()}] {title}"
        body = f"{title}\n\n{message}"

        if details:
            body += "\n\nDetails:\n"
            for key, value in details.items():
                body += f"- {key}: {value}\n"

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            html_body=html,
        )
