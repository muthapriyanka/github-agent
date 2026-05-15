from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlencode
import httpx


class GitHubOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = "repo read:user repo:status",
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, state: str) -> str:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post("https://github.com/login/oauth/access_token", data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("Failed to retrieve GitHub access token")
        return access_token


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def list_repo_files(self, owner: str, repo: str, ref: Optional[str] = None) -> List[Dict[str, Any]]:
        if ref is None:
            repo_data = await self.get_repository(owner, repo)
            ref = repo_data.get("default_branch", "main")

        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{ref}"
        params = {"recursive": "1"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return [item for item in data.get("tree", []) if item.get("type") == "blob"]

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[Sequence[str]] = None,
        per_page: int = 100,
        max_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        all_issues: List[Dict[str, Any]] = []
        per_page = min(per_page, 100)

        async with httpx.AsyncClient() as client:
            for page in range(1, max_pages + 1):
                params: Dict[str, Any] = {
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                }
                if labels:
                    params["labels"] = ",".join(labels)

                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                issues = response.json()
                all_issues.extend(issues)
                if len(issues) < per_page:
                    break

        return all_issues

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": 20}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def read_file(self, owner: str, repo: str, path: str, ref: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = list(labels)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if labels and exc.response.status_code == 422:
                    payload.pop("labels", None)
                    response = await client.post(url, headers=self.headers, json=payload)
                    response.raise_for_status()
                else:
                    raise
            return response.json()

    async def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        payload = {"body": body}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
