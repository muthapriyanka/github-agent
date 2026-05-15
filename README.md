# MCP GitHub Agent

An autonomous MCP server built in Python to connect a local Ollama model with GitHub, enabling issue triage, pull request reasoning, source code inspection, and agent-discovered GitHub issue filing.

## Features

- GitHub OAuth support for repository access
- MCP-style execution endpoint for tooling and workflow orchestration
- Ollama prompt orchestration
- Repository scanning for common code issues
- Optional filing of discovered findings as GitHub issues and comments
- Claude Code project instructions in root `CLAUDE.md`
- Reusable skill definitions in `docs/SKILLS.md`

## Setup

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies:

   ```bash
   python -m pip install -U pip
   python -m pip install -r requirements.txt
   ```

3. Run the server:

   ```bash
   uvicorn src.mcp_github_agent.server:APP --host 127.0.0.1 --port 8080
   ```

## Environment variables

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`
- `GITHUB_TOKEN`
- `LLM_PROVIDER=ollama`
- `LLM_MODEL`
- `OLLAMA_API_URL`
- `SESSION_SECRET`

## Main MCP tools

- `read_file`: fetch a file from GitHub.
- `issue_triage`: analyze an existing GitHub issue with Ollama.
- `pr_review`: analyze an existing pull request with Ollama.
- `discover_issues`: scan repository files and return findings without writing to GitHub.
- `discover_and_file_issues`: scan repository files, create GitHub issues, and post agent comments.
- `create_issue`: create a GitHub issue directly.
- `create_issue_comment`: comment on a GitHub issue directly.

Example request:

```json
{
  "tool": "discover_and_file_issues",
  "payload": {
    "github_token": "YOUR_TOKEN",
    "repository": "muthapriyanka/Prototype-Stackoverflow",
    "max_files": 100,
    "max_findings_to_file": 20,
    "use_ai_analysis": false
  }
}
```

## Documentation

- `CLAUDE.md`: optional Claude Code project instructions.
- `docs/SKILLS.md`: reusable MCP skill definitions and workflow templates.
