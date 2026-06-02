"""
Tests for GitHub API client service.

Uses respx to mock all GitHub API calls (no real API calls).
Tests retry logic, error handling, and response normalization.
"""

import pytest
import respx
from datetime import datetime
from httpx import Response

from app.services.github import GitHubClient, GitHubAPIError


@pytest.fixture
def github_client():
    """Fixture: GitHub client with test token."""
    return GitHubClient(access_token="test-token-12345")


@pytest.mark.asyncio
async def test_get_commits_success(github_client):
    """Test successful commits fetch."""
    with respx.mock:
        # Mock GitHub API response
        respx.get(
            "https://api.github.com/repos/test-org/test-repo/commits"
        ).mock(
            return_value=Response(
                200,
                json=[
                    {
                        "sha": "abc123",
                        "commit": {
                            "message": "Fix bug",
                            "author": {"name": "Alice", "date": "2026-04-20T10:00:00Z"},
                            "committer": {
                                "name": "Alice",
                                "date": "2026-04-20T10:00:00Z",
                            },
                        },
                        "author": {
                            "login": "alice",
                            "avatar_url": "https://...",
                        },
                    }
                ],
            )
        )

        commits = await github_client.get_commits("test-org", "test-repo")

        assert len(commits) == 1
        assert commits[0]["sha"] == "abc123"
        assert commits[0]["author_login"] == "alice"
        assert commits[0]["message"] == "Fix bug"


@pytest.mark.asyncio
async def test_get_commits_with_date_filters(github_client):
    """Test commits fetch with since/until filters."""
    with respx.mock:
        route = respx.get(
            "https://api.github.com/repos/test-org/test-repo/commits"
        )
        route.mock(return_value=Response(200, json=[]))

        since = datetime(2026, 4, 20)
        until = datetime(2026, 4, 25)

        await github_client.get_commits(
            "test-org", "test-repo", since=since, until=until
        )

        # Verify query params were sent
        request = route.calls.last.request
        assert b"since=" in request.url.query
        assert b"until=" in request.url.query


@pytest.mark.asyncio
async def test_get_commits_rate_limit(github_client):
    """Test rate limit handling (429)."""
    with respx.mock:
        respx.get(
            "https://api.github.com/repos/test-org/test-repo/commits"
        ).mock(
            return_value=Response(
                429,
                headers={"Retry-After": "60"},
            )
        )

        with pytest.raises(GitHubAPIError, match="Rate limited"):
            await github_client.get_commits("test-org", "test-repo")


@pytest.mark.asyncio
async def test_get_commits_server_error(github_client):
    """Test server error handling (500)."""
    with respx.mock:
        respx.get(
            "https://api.github.com/repos/test-org/test-repo/commits"
        ).mock(return_value=Response(500, text="Internal Server Error"))

        with pytest.raises(GitHubAPIError, match="500"):
            await github_client.get_commits("test-org", "test-repo")


@pytest.mark.asyncio
async def test_get_pull_requests_success(github_client):
    """Test successful PRs fetch."""
    with respx.mock:
        respx.get(
            "https://api.github.com/repos/test-org/test-repo/pulls"
        ).mock(
            return_value=Response(
                200,
                json=[
                    {
                        "id": 1,
                        "number": 42,
                        "title": "Feature: Add feature",
                        "state": "merged",
                        "user": {"login": "bob", "avatar_url": "https://..."},
                        "additions": 100,
                        "deletions": 50,
                        "changed_files": 3,
                        "review_comments": 5,
                        "created_at": "2026-04-20T10:00:00Z",
                        "merged_at": "2026-04-22T15:00:00Z",
                    }
                ],
            )
        )

        prs = await github_client.get_pull_requests("test-org", "test-repo")

        assert len(prs) == 1
        assert prs[0]["number"] == 42
        assert prs[0]["author_login"] == "bob"
        assert prs[0]["additions"] == 100
        assert prs[0]["state"] == "merged"


@pytest.mark.asyncio
async def test_get_contributors_success(github_client):
    """Test successful contributors fetch."""
    with respx.mock:
        respx.get(
            "https://api.github.com/repos/test-org/test-repo/contributors"
        ).mock(
            return_value=Response(
                200,
                json=[
                    {
                        "login": "alice",
                        "avatar_url": "https://...",
                        "contributions": 50,
                    },
                    {
                        "login": "bob",
                        "avatar_url": "https://...",
                        "contributions": 30,
                    },
                ],
            )
        )

        contributors = await github_client.get_contributors("test-org", "test-repo")

        assert len(contributors) == 2
        assert contributors[0]["github_login"] == "alice"
        assert contributors[0]["contributions"] == 50


@pytest.mark.asyncio
async def test_validate_webhook_signature_valid(github_client):
    """Test valid webhook signature validation."""
    payload = b'{"action": "opened"}'
    secret = "my-secret"

    import hmac
    import hashlib

    expected_sig = (
        "sha256="
        + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    )

    is_valid = await github_client.validate_webhook_signature(
        payload, expected_sig, secret
    )
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_webhook_signature_invalid(github_client):
    """Test invalid webhook signature validation."""
    payload = b'{"action": "opened"}'
    secret = "my-secret"
    wrong_sig = "sha256=wrong123"

    is_valid = await github_client.validate_webhook_signature(
        payload, wrong_sig, secret
    )
    assert is_valid is False


@pytest.mark.asyncio
async def test_validate_webhook_signature_bad_format(github_client):
    """Test webhook signature with bad format."""
    payload = b'{"action": "opened"}'
    bad_sig = "md5=notvalid"

    is_valid = await github_client.validate_webhook_signature(
        payload, bad_sig, "secret"
    )
    assert is_valid is False
