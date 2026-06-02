import httpx
import hmac
import hashlib
from datetime import datetime
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from app.providers.base import VCSProvider
from app.config import settings

class GitHubProvider(VCSProvider):
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        if access_token:
            self.client.headers["Authorization"] = f"Bearer {access_token}"

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(min=1, max=60),
        stop=stop_after_attempt(3)
    )
    async def _request(self, method: str, url: str, **kwargs):
        response = await self.client.request(method, url, **kwargs)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                import asyncio
                await asyncio.sleep(int(retry_after))
        response.raise_for_status()
        return response

    async def get_commits(self, repo_full_name: str, since: datetime, until: datetime) -> list[dict]:
        res = await self._request("GET", f"/repos/{repo_full_name}/commits", params={
            "since": since.isoformat(),
            "until": until.isoformat()
        })
        return res.json()

    async def get_pull_requests(self, repo_full_name: str, since: datetime) -> list[dict]:
        res = await self._request("GET", f"/repos/{repo_full_name}/pulls", params={
            "state": "all",
            "sort": "updated",
            "direction": "desc"
        })
        prs = res.json()
        filtered = []
        for pr in prs:
            pr_updated = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
            if pr_updated >= since:
                filtered.append(pr)
        return filtered

    async def get_org_repos(self, org_name: str) -> list[dict]:
        res = await self._request("GET", f"/orgs/{org_name}/repos", params={"type": "all"})
        return res.json()

    async def get_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self.client.get("https://api.github.com/user", headers=headers)
        response.raise_for_status()
        return response.json()

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        if not settings.github_webhook_secret:
            return False
        
        expected_signature = "sha256=" + hmac.new(
            settings.github_webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
