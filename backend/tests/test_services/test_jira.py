"""
Tests for Jira API client service.

Tests issue creation, comments, and transitions with mocked HTTP responses.
"""

import pytest
import respx
from httpx import Response

from app.services.jira import JiraClient, JiraAPIError


@pytest.fixture
def jira_client():
    """Fixture: Jira client."""
    return JiraClient(
        base_url="https://company.atlassian.net",
        username="test@company.com",
        api_token="test-token",
    )


@pytest.mark.asyncio
async def test_create_issue_success(jira_client):
    """Test successful Jira issue creation."""
    with respx.mock:
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue"
        ).mock(
            return_value=Response(
                201,
                json={
                    "id": "10000",
                    "key": "DEVP-123",
                    "self": "https://company.atlassian.net/rest/api/3/issue/10000",
                },
            )
        )

        result = await jira_client.create_issue(
            project_key="DEVP",
            issue_type="Task",
            summary="Fix bug",
            description="Bug in feature X",
            priority="High",
        )

        assert result["key"] == "DEVP-123"
        assert result["id"] == "10000"
        assert "DEVP-123" in result["url"]


@pytest.mark.asyncio
async def test_create_issue_with_labels(jira_client):
    """Test creating issue with labels and custom fields."""
    with respx.mock:
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue"
        ).mock(
            return_value=Response(
                201,
                json={
                    "id": "10001",
                    "key": "DEVP-124",
                    "self": "https://company.atlassian.net/rest/api/3/issue/10001",
                },
            )
        )

        result = await jira_client.create_issue(
            project_key="DEVP",
            issue_type="Bug",
            summary="Performance issue",
            description="Slow queries",
            labels=["performance", "database"],
            custom_fields={"customfield_10001": "value"},
        )

        assert result["key"] == "DEVP-124"


@pytest.mark.asyncio
async def test_create_issue_rate_limit(jira_client):
    """Test rate limit handling (429)."""
    with respx.mock:
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue"
        ).mock(
            return_value=Response(
                429,
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(JiraAPIError, match="Rate limited"):
            await jira_client.create_issue(
                project_key="DEVP",
                issue_type="Task",
                summary="Test",
                description="Test",
            )


@pytest.mark.asyncio
async def test_create_issue_auth_error(jira_client):
    """Test authentication error (401)."""
    with respx.mock:
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue"
        ).mock(
            return_value=Response(
                401,
                text="Invalid credentials",
            )
        )

        with pytest.raises(JiraAPIError):
            await jira_client.create_issue(
                project_key="DEVP",
                issue_type="Task",
                summary="Test",
                description="Test",
            )


@pytest.mark.asyncio
async def test_add_comment_success(jira_client):
    """Test adding comment to issue."""
    with respx.mock:
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue/DEVP-123/comment"
        ).mock(
            return_value=Response(
                201,
                json={
                    "id": "10000",
                    "self": "https://company.atlassian.net/rest/api/3/issue/10000/comment/10000",
                },
            )
        )

        result = await jira_client.add_comment(
            issue_key="DEVP-123",
            comment_text="Investigating this issue",
        )

        assert "id" in result


@pytest.mark.asyncio
async def test_transition_issue_success(jira_client):
    """Test transitioning issue to new status."""
    with respx.mock:
        # Mock GET to list transitions
        respx.get(
            "https://company.atlassian.net/rest/api/3/issue/DEVP-123/transitions"
        ).mock(
            return_value=Response(
                200,
                json={
                    "transitions": [
                        {"id": "11", "name": "To Do"},
                        {"id": "21", "name": "In Progress"},
                        {"id": "31", "name": "Done"},
                    ]
                },
            )
        )

        # Mock POST to transition
        respx.post(
            "https://company.atlassian.net/rest/api/3/issue/DEVP-123/transitions"
        ).mock(
            return_value=Response(204)
        )

        result = await jira_client.transition_issue(
            issue_key="DEVP-123",
            transition_name="In Progress",
        )

        assert result["status"] == "transitioned"
        assert result["issue_key"] == "DEVP-123"
