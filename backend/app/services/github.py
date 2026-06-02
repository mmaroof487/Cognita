"""
GitHub API Client Service — Fetch commits, PRs, and contributors from GitHub.

Uses httpx.AsyncClient with tenacity retries. Respects GitHub's rate limits
and 429 Retry-After headers. All calls use GitHub OAuth PAT from config.
"""

import logging
from datetime import datetime
from typing import Optional
from httpx import AsyncClient, Response
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from app.config import settings

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """GitHub API call failed."""

    pass


class GitHubClient:
    """Async GitHub API client with retry logic."""

    BASE_URL = "https://api.github.com"
    DEFAULT_TIMEOUT = 30

    def __init__(self, access_token: str):
        """
        Initialize GitHub client.

        Args:
            access_token: GitHub OAuth personal access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevPulse/0.1.0",
        }

    async def _get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict:
        """
        GET request with retry logic.

        Args:
            endpoint: API endpoint (e.g., "/repos/owner/repo/commits")
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            GitHubAPIError on failure after retries
        """

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
        )
        async def _fetch():
            async with AsyncClient(timeout=timeout) as client:
                url = f"{self.BASE_URL}{endpoint}"
                response = await client.get(url, headers=self.headers, params=params)

                # Handle rate limit (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"GitHub rate limit hit. Retry after {retry_after}s"
                    )
                    raise GitHubAPIError(
                        f"Rate limited (429). Retry after {retry_after}s"
                    )

                # Handle other errors
                if response.status_code >= 400:
                    logger.error(
                        f"GitHub API error {response.status_code}: {response.text}"
                    )
                    raise GitHubAPIError(
                        f"GitHub API error {response.status_code}: {response.text}"
                    )

                return response.json()

        try:
            return await _fetch()
        except RetryError as e:
            raise GitHubAPIError(f"Max retries exceeded: {e}")

    async def get_repo(
        self,
        owner: str,
        repo: str,
    ) -> dict:
        """
        Get repository details.

        Args:
            owner: GitHub organization/user
            repo: Repository name

        Returns:
            Dictionary with repo details.
        """
        endpoint = f"/repos/{owner}/{repo}"

        try:
            return await self._get(endpoint)
        except GitHubAPIError as e:
            logger.error(f"Error fetching repo: {e}")
            raise

    async def get_commits(
        self,
        owner: str,
        repo: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        per_page: int = 100,
    ) -> list[dict]:
        """
        Get commits for a repository.

        Args:
            owner: GitHub organization/user
            repo: Repository name
            since: Only commits after this datetime
            until: Only commits before this datetime
            per_page: Results per page (1-100)

        Returns:
            List of commit dictionaries
        """
        params = {"per_page": min(per_page, 100)}

        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        endpoint = f"/repos/{owner}/{repo}/commits"

        try:
            data = await self._get(endpoint, params)
            commits = data if isinstance(data, list) else []

            normalized = [
                {
                    "sha": c.get("sha", ""),
                    "message": (c.get("commit") or {}).get("message", ""),
                    "author": (c.get("commit") or {}).get("author", {}).get("name"),
                    "author_login": (c.get("author") or {}).get("login"),
                    "author_avatar_url": (c.get("author") or {}).get("avatar_url"),
                    "additions": 0,  # Not in list endpoint, requires per-commit fetch
                    "deletions": 0,
                    "files_changed": 0,
                    "committed_at": (c.get("commit") or {})
                    .get("committer", {})
                    .get("date"),
                }
                for c in commits
            ]

            logger.info(
                f"Fetched {len(normalized)} commits from {owner}/{repo}"
            )
            return normalized

        except GitHubAPIError as e:
            logger.error(f"Error fetching commits: {e}")
            raise

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        per_page: int = 100,
    ) -> list[dict]:
        """
        Get pull requests for a repository.

        Args:
            owner: GitHub organization/user
            repo: Repository name
            state: "open", "closed", or "all"
            per_page: Results per page (1-100)

        Returns:
            List of PR dictionaries
        """
        params = {"state": state, "per_page": min(per_page, 100)}
        endpoint = f"/repos/{owner}/{repo}/pulls"

        try:
            data = await self._get(endpoint, params)
            prs = data if isinstance(data, list) else []

            normalized = [
                {
                    "id": p.get("id"),
                    "number": p.get("number"),
                    "title": p.get("title", ""),
                    "state": p.get("state", ""),
                    "author_login": p.get("user", {}).get("login"),
                    "author_avatar_url": p.get("user", {}).get("avatar_url"),
                    "additions": p.get("additions", 0),
                    "deletions": p.get("deletions", 0),
                    "changed_files": p.get("changed_files", 0),
                    "review_comments": p.get("review_comments", 0),
                    "created_at": p.get("created_at"),
                    "merged_at": p.get("merged_at"),
                }
                for p in prs
            ]

            logger.info(f"Fetched {len(normalized)} PRs from {owner}/{repo}")
            return normalized

        except GitHubAPIError as e:
            logger.error(f"Error fetching PRs: {e}")
            raise

    async def get_contributors(
        self,
        owner: str,
        repo: str,
        per_page: int = 100,
    ) -> list[dict]:
        """
        Get contributors for a repository.

        Args:
            owner: GitHub organization/user
            repo: Repository name
            per_page: Results per page (1-100)

        Returns:
            List of contributor dictionaries
        """
        params = {"per_page": min(per_page, 100)}
        endpoint = f"/repos/{owner}/{repo}/contributors"

        try:
            data = await self._get(endpoint, params)
            contributors = data if isinstance(data, list) else []

            normalized = [
                {
                    "github_login": c.get("login", ""),
                    "avatar_url": c.get("avatar_url"),
                    "contributions": c.get("contributions", 0),
                }
                for c in contributors
            ]

            logger.info(
                f"Fetched {len(normalized)} contributors from {owner}/{repo}"
            )
            return normalized

        except GitHubAPIError as e:
            logger.error(f"Error fetching contributors: {e}")
            raise

    async def validate_webhook_signature(
        self,
        payload_body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Validate GitHub webhook signature.

        GitHub sends X-Hub-Signature-256 header with HMAC-SHA256(secret, payload).

        Args:
            payload_body: Raw request body bytes
            signature: X-Hub-Signature-256 header value (format: "sha256=...")
            secret: Webhook secret from GitHub settings

        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib

        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format")
            return False

        expected_signature = (
            "sha256="
            + hmac.new(
                secret.encode(),
                payload_body,
                hashlib.sha256,
            ).hexdigest()
        )

        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning("Webhook signature validation failed")

        return is_valid
