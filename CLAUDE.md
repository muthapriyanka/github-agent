# CLAUDE.md

This file gives Claude Code project-specific instructions when working in this repository.

## Project Overview

This repository is a Python FastAPI MCP-style GitHub agent. It connects to GitHub with a user-provided token and uses a local Ollama model for LLM reasoning.

The project does not currently use Anthropic or the Claude API at runtime. Claude Code may use this file as coding context, but the application itself sends prompts to Ollama through `src/mcp_github_agent/llm_client.py`.

## Main Files

- `src/mcp_github_agent/server.py`: FastAPI app, auth routes, and `/mcp/execute` tool dispatch.
- `src/mcp_github_agent/github_client.py`: GitHub OAuth and GitHub REST API wrapper.
- `src/mcp_github_agent/llm_client.py`: Ollama-only LLM client.
- `src/mcp_github_agent/issue_discovery.py`: Repository scanning rules and issue body/title helpers.
- `src/mcp_github_agent/workflows.py`: Prompt builders for issue triage, PR review, and discovered issue analysis.
- `src/mcp_github_agent/models.py`: Pydantic request/response/config models.
- `docs/SKILLS.md`: Documentation for supported MCP tools.

## Runtime Behavior

The server exposes:

- `GET /_health`
- `GET /tools`
- `GET /auth/github/login`
- `GET /auth/github/callback`
- `POST /mcp/execute`

Supported MCP tools:

- `read_file`
- `issue_triage`
- `pr_review`
- `create_issue`
- `create_issue_comment`
- `discover_issues`
- `discover_and_file_issues`

Use `discover_issues` for a preview-only scan. Use `discover_and_file_issues` only when the user explicitly wants GitHub issues created.

## Local Commands

Run syntax checks:

```bash
python3 -m py_compile src/mcp_github_agent/*.py
```

Run the server:

```bash
./venv/bin/uvicorn src.mcp_github_agent.server:APP --host 127.0.0.1 --port 8080
```

Check health:

```bash
curl http://127.0.0.1:8080/_health
```

## Engineering Guidelines

- Keep GitHub HTTP calls inside `github_client.py`.
- Keep Ollama/LLM calls inside `llm_client.py`.
- Keep prompt text in `workflows.py`.
- Keep issue scanning rules in `issue_discovery.py`.
- Keep `server.py` focused on routing, validation, and tool orchestration.
- Do not add Anthropic or Claude API code unless the user explicitly asks for provider support.
- Do not create GitHub issues unless the user explicitly asks for a write action.
- Prefer preview scans before write actions when changing GitHub state.

## Environment

Common environment variables:

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`
- `GITHUB_TOKEN`
- `LLM_PROVIDER=ollama`
- `LLM_MODEL=mistral`
- `OLLAMA_API_URL=http://localhost:11434`
- `SESSION_SECRET`

## Notes For Claude Code

If asked to make this project use Claude API, add it as an optional provider rather than replacing Ollama. The current default should remain local Ollama.

If asked to run `discover_and_file_issues`, confirm that the user understands it creates real GitHub issues, unless the request already clearly says to run the write tool.
