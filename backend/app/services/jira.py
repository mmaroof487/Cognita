"""
Jira API client for creating tickets from agent actions.

Handles ticket creation with formatted summaries, descriptions, and metadata.
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class JiraAPIError(Exception):
    """Raised when Jira API call fails."""

    pass


class JiraClient:
    """Jira API client for ticket operations."""

    def __init__(self, base_url: str, username: str, api_token: str):
        """
        Initialize Jira client.

        Args:
            base_url: Jira instance URL (e.g., https://company.atlassian.net)
            username: Jira username or email
            api_token: Jira API token (generate from account settings)
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.auth = (username, api_token)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        priority: str = "Medium",
        labels: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None,
    ) -> dict:
        """
        Create a Jira issue.

        Args:
            project_key: Jira project key (e.g., "DEVP")
            issue_type: Issue type (e.g., "Bug", "Task", "Story")
            summary: Issue title
            description: Issue description (supports Jira markup)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: Optional labels to apply
            custom_fields: Optional custom field values {field_id: value}

        Returns:
            Created issue details: {key, id, url, self}

        Raises:
            JiraAPIError: On API failure
        """
        url = f"{self.base_url}/rest/api/3/issue"

        # Build payload
        payload = {
            "fields": {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": summary,
                "description": {
                    "version": 3,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description,
                                }
                            ],
                        }
                    ],
                },
                "priority": {"name": priority},
            }
        }

        # Add labels if provided
        if labels:
            payload["fields"]["labels"] = labels

        # Add custom fields
        if custom_fields:
            payload["fields"].update(custom_fields)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    auth=self.auth,
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                )

                if response.status_code == 429:
                    logger.warning(
                        f"Jira rate limited. Retry-After: {response.headers.get('Retry-After')}"
                    )
                    raise JiraAPIError("Rate limited")

                if response.status_code >= 400:
                    error_text = response.text
                    logger.error(f"Jira API error {response.status_code}: {error_text}")
                    raise JiraAPIError(f"Jira API error {response.status_code}: {error_text}")

                result = response.json()
                issue_key = result.get("key")
                issue_id = result.get("id")

                logger.info(f"Created Jira issue: {issue_key}")

                return {
                    "key": issue_key,
                    "id": issue_id,
                    "url": f"{self.base_url}/browse/{issue_key}",
                    "self": result.get("self"),
                }

        except httpx.RequestError as e:
            logger.error(f"Jira API connection error: {e}")
            raise JiraAPIError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating Jira issue: {e}")
            raise JiraAPIError(f"Unexpected error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def add_comment(self, issue_key: str, comment_text: str) -> dict:
        """
        Add comment to existing issue.

        Args:
            issue_key: Jira issue key (e.g., "DEVP-123")
            comment_text: Comment text (supports Jira markup)

        Returns:
            Comment details
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"

        payload = {
            "body": {
                "version": 3,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}],
                    }
                ],
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    auth=self.auth,
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                )

                if response.status_code >= 400:
                    raise JiraAPIError(f"Jira API error {response.status_code}")

                return response.json()

        except httpx.RequestError as e:
            raise JiraAPIError(f"Connection error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def transition_issue(
        self, issue_key: str, transition_name: str, comment: Optional[str] = None
    ) -> dict:
        """
        Transition issue to new status.

        Args:
            issue_key: Jira issue key
            transition_name: Transition name (e.g., "In Progress", "Done")
            comment: Optional comment when transitioning

        Returns:
            Updated issue details
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"

        # Get available transitions
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    auth=self.auth,
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                )

                if resp.status_code >= 400:
                    raise JiraAPIError(f"Failed to get transitions: {resp.status_code}")

                transitions = resp.json().get("transitions", [])
                transition_id = next(
                    (t["id"] for t in transitions if t["name"] == transition_name),
                    None,
                )

                if not transition_id:
                    raise JiraAPIError(f"Transition '{transition_name}' not found")

                # Perform transition
                payload = {"transition": {"id": transition_id}}

                if comment:
                    payload["update"] = {
                        "comment": [
                            {
                                "add": {
                                    "body": {
                                        "version": 3,
                                        "type": "doc",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": comment}
                                                ],
                                            }
                                        ],
                                    }
                                }
                            }
                        ]
                    }

                response = await client.post(
                    url,
                    json=payload,
                    auth=self.auth,
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                )

                if response.status_code >= 400:
                    raise JiraAPIError(f"Transition failed: {response.status_code}")

                return {"status": "transitioned", "issue_key": issue_key}

        except httpx.RequestError as e:
            raise JiraAPIError(f"Connection error: {e}") from e
