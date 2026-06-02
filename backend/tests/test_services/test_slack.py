"""
Tests for Slack API client service.

Tests message sending with webhook and bot token modes.
"""

import pytest
import respx
from httpx import Response

from app.services.slack import SlackClient, SlackAPIError


@pytest.fixture
def slack_client_webhook():
    """Fixture: Slack client with webhook."""
    return SlackClient(
        webhook_url="https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    )


@pytest.fixture
def slack_client_bot():
    """Fixture: Slack client with bot token."""
    return SlackClient(
        bot_token="xoxb-your-token"
    )


@pytest.mark.asyncio
async def test_send_message_webhook(slack_client_webhook):
    """Test sending message via webhook."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(200))

        result = await slack_client_webhook.send_message(
            text="Test message"
        )

        assert result["ok"] is True
        assert result["via"] == "webhook"


@pytest.mark.asyncio
async def test_send_message_with_blocks(slack_client_webhook):
    """Test sending message with rich blocks."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(200))

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Bold text*"}
            }
        ]

        result = await slack_client_webhook.send_message(
            text="Fallback",
            blocks=blocks,
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_message_bot_token(slack_client_bot):
    """Test sending message via bot token."""
    with respx.mock:
        respx.post("https://slack.com/api/chat.postMessage").mock(
            return_value=Response(
                200,
                json={
                    "ok": True,
                    "channel": "C1234567",
                    "ts": "1503435956.000247",
                },
            )
        )

        result = await slack_client_bot.send_message(
            text="Test message",
            channel="C1234567",
        )

        assert result["ok"] is True
        assert result["channel"] == "C1234567"


@pytest.mark.asyncio
async def test_send_message_bot_token_error(slack_client_bot):
    """Test bot token error handling."""
    with respx.mock:
        respx.post("https://slack.com/api/chat.postMessage").mock(
            return_value=Response(
                200,
                json={
                    "ok": False,
                    "error": "channel_not_found",
                },
            )
        )

        with pytest.raises(SlackAPIError, match="channel_not_found"):
            await slack_client_bot.send_message(
                text="Test",
                channel="C_INVALID",
            )


@pytest.mark.asyncio
async def test_send_rich_message(slack_client_webhook):
    """Test sending rich formatted message."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(200))

        result = await slack_client_webhook.send_rich_message(
            title="Important Update",
            text="Something needs attention",
            fields={
                "Priority": "High",
                "Status": "Open",
            },
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_alert_warning(slack_client_webhook):
    """Test sending alert with warning severity."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(200))

        result = await slack_client_webhook.send_alert(
            title="Performance Degradation",
            message="Response time > 5s",
            severity="warning",
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_alert_critical(slack_client_webhook):
    """Test sending critical alert."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(200))

        result = await slack_client_webhook.send_alert(
            title="System Down",
            message="Production database unreachable",
            severity="critical",
        )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_send_message_webhook_error(slack_client_webhook):
    """Test webhook error handling."""
    with respx.mock:
        respx.post(
            "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        ).mock(return_value=Response(404))

        with pytest.raises(SlackAPIError):
            await slack_client_webhook.send_message(text="Test")


@pytest.mark.asyncio
async def test_send_message_no_config():
    """Test error when no webhook or bot token configured."""
    client = SlackClient()

    with pytest.raises(SlackAPIError, match="No webhook"):
        await client.send_message(text="Test")
