# GitHub Agent

An autonomous MCP server built in Python to connect a local Ollama model with GitHub, enabling issue triage, pull request reasoning, source code inspection, and agent-discovered GitHub issue filing.

## Features

- GitHub OAuth support for repository access
- MCP-style execution endpoint for tooling and workflow orchestration
- Ollama prompt orchestration
- Repository scanning for common code issues
- Optional filing of discovered findings as GitHub issues and comments
- Claude Code project instructions in root `CLAUDE.md`
- Reusable skill definitions in `docs/SKILLS.md`
