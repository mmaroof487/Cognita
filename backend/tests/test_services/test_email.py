"""
Tests for Email client service.

Tests SMTP email sending with mocked SMTP server.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.email import EmailClient, EmailError


@pytest.fixture
def email_client():
    """Fixture: Email client."""
    return EmailClient(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="test@gmail.com",
        password="app-password",
        from_address="noreply@devpulse.ai",
    )


@pytest.mark.asyncio
async def test_send_email_success(email_client):
    """Test successful email sending."""
    with patch("smtplib.SMTP") as mock_smtp:
        # Mock SMTP connection
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_email(
            to="user@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result["ok"] is True
        assert result["to"] == ["user@example.com"]
        assert result["subject"] == "Test Subject"

        # Verify SMTP methods called
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "app-password")
        mock_server.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_multiple_recipients(email_client):
    """Test sending to multiple recipients."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_email(
            to=["user1@example.com", "user2@example.com"],
            subject="Test",
            body="Body",
        )

        assert result["ok"] is True
        assert len(result["to"]) == 2


@pytest.mark.asyncio
async def test_send_email_with_html(email_client):
    """Test sending HTML email."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_email(
            to="user@example.com",
            subject="HTML Email",
            body="Plain text body",
            html_body="<html><body>HTML body</body></html>",
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_email_with_cc_bcc(email_client):
    """Test sending with CC and BCC."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )

        assert result["ok"] is True

        # Verify sendmail called with all recipients
        sendmail_call = mock_server.sendmail.call_args
        recipients = sendmail_call[0][1]
        assert "user@example.com" in recipients
        assert "cc@example.com" in recipients
        assert "bcc@example.com" in recipients


@pytest.mark.asyncio
async def test_send_email_auth_error(email_client):
    """Test authentication error."""
    with patch("smtplib.SMTP") as mock_smtp:
        import smtplib
        
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(401, "Invalid credentials")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with pytest.raises(EmailError, match="Authentication failed"):
            await email_client.send_email(
                to="user@example.com",
                subject="Test",
                body="Body",
            )


@pytest.mark.asyncio
async def test_send_email_smtp_error(email_client):
    """Test SMTP connection error."""
    with patch("smtplib.SMTP") as mock_smtp:
        import smtplib
        
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("SMTP error")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with pytest.raises(EmailError, match="SMTP error"):
            await email_client.send_email(
                to="user@example.com",
                subject="Test",
                body="Body",
            )


@pytest.mark.asyncio
async def test_send_alert_info(email_client):
    """Test sending info alert email."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_alert(
            to="admin@example.com",
            title="System Update",
            message="Scheduled maintenance completed",
            severity="info",
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_alert_error_with_details(email_client):
    """Test sending error alert with details."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_alert(
            to="admin@example.com",
            title="High Memory Usage",
            message="Application memory exceeded threshold",
            severity="error",
            details={
                "Current Usage": "95%",
                "Threshold": "90%",
                "Pod": "app-prod-01",
            },
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_alert_critical(email_client):
    """Test sending critical alert."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_client.send_alert(
            to="oncall@example.com",
            title="Database Connection Failed",
            message="Primary database connection lost",
            severity="critical",
            details={
                "Service": "Auth API",
                "Time": "2026-04-26T14:30:00Z",
            },
        )

        assert result["ok"] is True
