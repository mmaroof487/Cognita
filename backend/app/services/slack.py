"""
Slack API client for sending notifications.

Handles message posting, thread replies, and rich formatting.
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SlackAPIError(Exception):
    """Raised when Slack API call fails."""

    pass


class SlackClient:
    """Slack API client for notifications."""

    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None):
        """
        Initialize Slack client.

        Args:
            webhook_url: Incoming webhook URL (for simple messages)
            bot_token: Bot token (for more complex operations)
        """
        self.webhook_url = webhook_url
        self.bot_token = bot_token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> dict:
        """
        Send Slack message via webhook or bot token.

        Args:
            text: Plain text message (fallback)
            channel: Channel ID or name (required for bot token)
            blocks: Rich message blocks (Slack Block Kit)
            thread_ts: Thread timestamp to reply in

        Returns:
            Response details: {ok, ts, channel}

        Raises:
            SlackAPIError: On API failure
        """
        # Use webhook if available (simpler, no auth needed at runtime)
        if self.webhook_url:
            payload = {"text": text}

            if blocks:
                payload["blocks"] = blocks

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        timeout=10.0,
                    )

                    if response.status_code != 200:
                        logger.error(f"Slack webhook error {response.status_code}: {response.text}")
                        raise SlackAPIError(f"Webhook error {response.status_code}")

                    logger.info("Message sent to Slack via webhook")

                    return {
                        "ok": True,
                        "via": "webhook",
                    }

            except httpx.RequestError as e:
                logger.error(f"Slack webhook connection error: {e}")
                raise SlackAPIError(f"Connection error: {e}") from e

        # Fallback to bot token if webhook not available
        elif self.bot_token and channel:
            url = "https://slack.com/api/chat.postMessage"

            payload = {
                "channel": channel,
                "text": text,
            }

            if blocks:
                payload["blocks"] = blocks

            if thread_ts:
                payload["thread_ts"] = thread_ts

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.bot_token}"},
                        timeout=10.0,
                    )

                    result = response.json()

                    if not result.get("ok"):
                        error = result.get("error", "Unknown error")
                        logger.error(f"Slack API error: {error}")
                        raise SlackAPIError(error)

                    logger.info(f"Message sent to {channel}")

                    return {
                        "ok": True,
                        "ts": result.get("ts"),
                        "channel": result.get("channel"),
                    }

            except httpx.RequestError as e:
                logger.error(f"Slack API connection error: {e}")
                raise SlackAPIError(f"Connection error: {e}") from e

        else:
            raise SlackAPIError("No webhook URL or bot token configured")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def send_rich_message(
        self,
        title: str,
        text: str,
        channel: Optional[str] = None,
        color: str = "#36a64f",
        fields: Optional[dict] = None,
        actions: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send rich formatted message with blocks.

        Args:
            title: Message title
            text: Message text
            channel: Target channel
            color: Left border color (hex)
            fields: Key-value pairs to display
            actions: Action buttons

        Returns:
            Response details
        """
        # Build blocks
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
        ]

        # Add fields section if provided
        if fields:
            field_blocks = [
                {
                    "type": "mrkdwn",
                    "text": f"*{k}*\n{v}",
                }
                for k, v in fields.items()
            ]

            blocks.append(
                {
                    "type": "section",
                    "fields": field_blocks,
                }
            )

        # Add actions if provided
        if actions:
            blocks.append(
                {
                    "type": "actions",
                    "elements": actions,
                }
            )

        return await self.send_message(text, channel=channel, blocks=blocks)

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channel: Optional[str] = None,
    ) -> dict:
        """
        Send alert-style message.

        Args:
            title: Alert title
            message: Alert message
            severity: "info", "warning", "error", "critical"
            channel: Target channel

        Returns:
            Response details
        """
        color_map = {
            "info": "#36a64f",  # Green
            "warning": "#f4a460",  # Orange
            "error": "#e74c3c",  # Red
            "critical": "#8b0000",  # Dark red
        }

        color = color_map.get(severity, "#36a64f")
        severity_icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨",
        }.get(severity, "📢")

        text = f"{severity_icon} *{severity.upper()}*\n{message}"

        return await self.send_rich_message(
            title=title,
            text=text,
            channel=channel,
            color=color,
        )
