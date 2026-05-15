from __future__ import annotations
import base64
import os
import secrets
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import GitHubOAuthConfig, MCPRequest, MCPResponse
from .github_client import GitHubClient, GitHubOAuthClient
from .issue_discovery import (
    DEFAULT_LABELS,
    IssueFinding,
    build_analysis_comment,
    build_issue_body,
    build_issue_title,
    scan_content_for_issues,
    should_scan_file,
    summarize_findings,
)
from .llm_client import LLMClient
from .workflows import discovered_issue_analysis_prompt, issue_triage_prompt, pr_review_prompt

load_dotenv()

APP = FastAPI(title="MCP GitHub Agent")
APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

GITHUB_OAUTH_CONFIG = GitHubOAuthConfig(
    client_id=os.getenv("GITHUB_CLIENT_ID", ""),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
    redirect_uri=os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8080/auth/github/callback"),
)
GITHUB_OAUTH_CLIENT = GitHubOAuthClient(
    client_id=GITHUB_OAUTH_CONFIG.client_id,
    client_secret=GITHUB_OAUTH_CONFIG.client_secret,
    redirect_uri=GITHUB_OAUTH_CONFIG.redirect_uri,
)
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))
OAUTH_STATE_STORE: Dict[str, str] = {}
ACCESS_TOKENS: Dict[str, str] = {}


def _split_repository(repository: Optional[str]) -> tuple[str, str]:
    owner, repo_name = (repository or "").split("/") if repository and "/" in repository else (None, None)
    if not owner or not repo_name:
        raise HTTPException(status_code=400, detail="repository must be provided as owner/repo")
    return owner, repo_name


def _payload_int(payload: Dict[str, Any], key: str, default: int, minimum: int, maximum: int) -> int:
    value = int(payload.get(key, default))
    return max(minimum, min(value, maximum))


def _payload_bool(payload: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _payload_labels(payload: Dict[str, Any]) -> List[str]:
    labels = payload.get("labels", DEFAULT_LABELS)
    if labels is None:
        return []
    if isinstance(labels, str):
        return [labels]
    return [str(label) for label in labels]


def _decode_file_content(file_data: Dict[str, Any]) -> str:
    if file_data.get("encoding") != "base64":
        raise ValueError("Only base64 encoded GitHub file content is supported")
    content = file_data.get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="replace")


async def _scan_repository(
    client: GitHubClient,
    owner: str,
    repo_name: str,
    ref: Optional[str],
    max_files: int,
    max_file_bytes: int,
) -> Dict[str, Any]:
    tree = await client.list_repo_files(owner, repo_name, ref)
    candidates = [
        item
        for item in tree
        if should_scan_file(item.get("path", "")) and int(item.get("size", 0)) <= max_file_bytes
    ][:max_files]

    findings: List[IssueFinding] = []
    file_contents: Dict[str, str] = {}
    errors: List[Dict[str, str]] = []

    for item in candidates:
        path = item.get("path", "")
        try:
            file_data = await client.read_file(owner, repo_name, path, ref)
            content = _decode_file_content(file_data)
            file_findings = scan_content_for_issues(content, path)
            if file_findings:
                file_contents[path] = content
                findings.extend(file_findings)
        except Exception as exc:
            errors.append({"path": path, "error": str(exc)})

    return {
        "scanned_files": len(candidates),
        "findings": findings,
        "file_contents": file_contents,
        "errors": errors,
    }


def run_app() -> None:
    import uvicorn
    uvicorn.run("src.mcp_github_agent.server:APP", host="0.0.0.0", port=8080, reload=True)


@APP.get("/_health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@APP.get("/auth/github/login")
async def github_login(state: Optional[str] = Query(None)) -> RedirectResponse:
    state_token = secrets.token_urlsafe(16) if state is None else state
    OAUTH_STATE_STORE[state_token] = "pending"
    url = GITHUB_OAUTH_CLIENT.build_authorization_url(state_token)
    return RedirectResponse(url)


@APP.get("/auth/github/callback")
async def github_callback(code: str, state: str) -> JSONResponse:
    stored = OAUTH_STATE_STORE.get(state)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        access_token = await GITHUB_OAUTH_CLIENT.exchange_code_for_token(code, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ACCESS_TOKENS[state] = access_token
    return JSONResponse({"status": "authenticated", "state": state})


@APP.post("/mcp/execute")
async def execute_mcp(request: MCPRequest) -> MCPResponse:
    try:
        token = request.payload.get("github_token")
        if not token:
            raise HTTPException(status_code=400, detail="github_token is required in payload")

        client = GitHubClient(token=token)
        repo = request.payload.get("repository")
        owner, repo_name = _split_repository(repo)

        if request.tool == "issue_triage":
            issue_number = int(request.payload.get("issue_number", 0))
            issue = await client.get_issue(owner, repo_name, issue_number)
            llm = LLMClient()
            prompt = issue_triage_prompt(issue, request.payload.get("repository", ""))
            answer = await llm.send_prompt(prompt)
            return MCPResponse(status="ok", output=answer, tool_output={"issue": issue})

        if request.tool == "pr_review":
            pr_number = int(request.payload.get("pr_number", 0))
            pr = await client.get_pull_request(owner, repo_name, pr_number)
            changed_files = request.payload.get("changed_files", "")
            llm = LLMClient()
            prompt = pr_review_prompt(pr, changed_files, request.payload.get("repository", ""))
            answer = await llm.send_prompt(prompt)
            return MCPResponse(status="ok", output=answer, tool_output={"pr": pr})

        if request.tool == "read_file":
            path = request.payload.get("path")
            ref = request.payload.get("ref")
            file_data = await client.read_file(owner, repo_name, path, ref)
            content = _decode_file_content(file_data)
            return MCPResponse(status="ok", output=f"File: {file_data.get('name')}\n\n{content}", tool_output={"file": file_data.get("name"), "size": file_data.get("size")})

        if request.tool == "create_issue":
            title = request.payload.get("title")
            body = request.payload.get("body", "")
            if not title:
                raise HTTPException(status_code=400, detail="title is required")

            issue = await client.create_issue(owner, repo_name, str(title), str(body), _payload_labels(request.payload))
            return MCPResponse(
                status="ok",
                output=f"Created issue #{issue.get('number')}: {issue.get('html_url')}",
                tool_output={"issue": issue},
            )

        if request.tool == "create_issue_comment":
            issue_number = int(request.payload.get("issue_number", 0))
            body = request.payload.get("body")
            if not issue_number or not body:
                raise HTTPException(status_code=400, detail="issue_number and body are required")

            comment = await client.create_issue_comment(owner, repo_name, issue_number, str(body))
            return MCPResponse(
                status="ok",
                output=f"Commented on issue #{issue_number}: {comment.get('html_url')}",
                tool_output={"comment": comment},
            )

        if request.tool == "discover_issues":
            ref = request.payload.get("ref")
            max_files = _payload_int(request.payload, "max_files", 100, 1, 500)
            max_file_bytes = _payload_int(request.payload, "max_file_bytes", 200_000, 1_000, 1_000_000)
            scan = await _scan_repository(client, owner, repo_name, ref, max_files, max_file_bytes)
            findings = scan["findings"]
            repository = request.payload.get("repository", "")
            return MCPResponse(
                status="ok",
                output=summarize_findings(repository, scan["scanned_files"], findings),
                tool_output={
                    "repository": repository,
                    "scanned_files": scan["scanned_files"],
                    "total_findings": len(findings),
                    "findings": [finding.to_dict() for finding in findings],
                    "errors": scan["errors"],
                },
            )

        if request.tool == "discover_and_file_issues":
            ref = request.payload.get("ref")
            max_files = _payload_int(request.payload, "max_files", 100, 1, 500)
            max_file_bytes = _payload_int(request.payload, "max_file_bytes", 200_000, 1_000, 1_000_000)
            max_findings_to_file = _payload_int(request.payload, "max_findings_to_file", 20, 1, 100)
            use_ai_analysis = _payload_bool(request.payload, "use_ai_analysis", False)
            labels = _payload_labels(request.payload)
            repository = request.payload.get("repository", "")

            scan = await _scan_repository(client, owner, repo_name, ref, max_files, max_file_bytes)
            findings = scan["findings"][:max_findings_to_file]
            existing_issues = await client.list_issues(owner, repo_name, state="all", max_pages=5)
            existing_titles = {
                issue.get("title")
                for issue in existing_issues
                if "pull_request" not in issue and issue.get("title")
            }

            llm = LLMClient() if use_ai_analysis else None
            filed: List[Dict[str, Any]] = []
            skipped: List[Dict[str, str]] = []
            errors: List[Dict[str, str]] = list(scan["errors"])

            for finding in findings:
                title = build_issue_title(finding)
                if title in existing_titles:
                    skipped.append({"title": title, "reason": "matching issue title already exists"})
                    continue

                try:
                    body = build_issue_body(repository, finding)
                    issue = await client.create_issue(owner, repo_name, title, body, labels)

                    ai_analysis = None
                    if llm is not None:
                        code_excerpt = scan["file_contents"].get(finding.file_path, "")[:4000]
                        prompt = discovered_issue_analysis_prompt(finding.to_dict(), code_excerpt, repository)
                        try:
                            ai_analysis = await llm.send_prompt(prompt, max_tokens=700)
                        except Exception as exc:
                            errors.append({"path": finding.file_path, "error": f"AI analysis failed: {exc}"})

                    comment = await client.create_issue_comment(
                        owner,
                        repo_name,
                        int(issue.get("number")),
                        build_analysis_comment(finding, ai_analysis),
                    )
                    filed.append(
                        {
                            "number": issue.get("number"),
                            "title": title,
                            "url": issue.get("html_url"),
                            "comment_url": comment.get("html_url"),
                        }
                    )
                    existing_titles.add(title)
                except Exception as exc:
                    errors.append({"path": finding.file_path, "error": str(exc)})

            output = (
                f"Scanned {scan['scanned_files']} files and found {len(scan['findings'])} issue(s). "
                f"Filed {len(filed)} GitHub issue(s), skipped {len(skipped)} duplicate(s)."
            )
            return MCPResponse(
                status="ok",
                output=output,
                tool_output={
                    "repository": repository,
                    "scanned_files": scan["scanned_files"],
                    "total_findings": len(scan["findings"]),
                    "filed": filed,
                    "skipped": skipped,
                    "errors": errors,
                },
            )

        raise HTTPException(status_code=400, detail=f"Unsupported tool: {request.tool}")
    except HTTPException:
        raise
    except Exception as e:
        return MCPResponse(status="error", output=f"Error: {str(e)}")


@APP.get("/tools")
async def list_tools() -> Dict[str, list[str]]:
    return {
        "supported_tools": [
            "issue_triage",
            "pr_review",
            "read_file",
            "create_issue",
            "create_issue_comment",
            "discover_issues",
            "discover_and_file_issues",
        ]
    }
