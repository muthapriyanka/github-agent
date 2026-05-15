# SKILLS.md

This document describes the MCP tools exposed by the GitHub agent server.

The server runs locally with FastAPI, talks to GitHub through `GitHubClient`, and uses Ollama for LLM reasoning through `LLMClient`.

## Tools

### `read_file`

Read a repository file from GitHub.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `path`: repo-relative file path
- `ref`: optional branch, tag, or commit SHA
- `github_token`: GitHub access token

Output:

- File name, size, and decoded content

### `issue_triage`

Fetch an existing GitHub issue and ask Ollama to analyze severity, priority, labels, next steps, and missing information.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `issue_number`: issue number
- `github_token`: GitHub access token

Output:

- Triage summary from Ollama
- Raw GitHub issue payload in `tool_output`

### `pr_review`

Fetch an existing GitHub pull request and ask Ollama to review it with the provided changed-file context.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `pr_number`: pull request number
- `changed_files`: diff or summary text
- `github_token`: GitHub access token

Output:

- Review summary from Ollama
- Raw GitHub PR payload in `tool_output`

### `create_issue`

Create a GitHub issue directly.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `title`: issue title
- `body`: issue body
- `labels`: optional labels
- `github_token`: GitHub access token

Output:

- Created issue URL and raw GitHub issue payload

### `create_issue_comment`

Post a comment on an existing GitHub issue.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `issue_number`: issue number
- `body`: comment body
- `github_token`: GitHub access token

Output:

- Created comment URL and raw GitHub comment payload

### `discover_issues`

Scan repository files with local rules and return findings without writing to GitHub.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `github_token`: GitHub access token
- `ref`: optional branch, tag, or commit SHA
- `max_files`: optional scan limit, default `100`
- `max_file_bytes`: optional per-file size limit, default `200000`

Output:

- Scan summary
- Finding list in `tool_output`
- Any scan errors

### `discover_and_file_issues`

Scan repository files, create GitHub issues for findings, and post agent comments.

Input:

- `repository`: GitHub repository in `owner/repo` format
- `github_token`: GitHub access token
- `ref`: optional branch, tag, or commit SHA
- `max_files`: optional scan limit, default `100`
- `max_file_bytes`: optional per-file size limit, default `200000`
- `max_findings_to_file`: optional issue creation limit, default `20`
- `use_ai_analysis`: optional boolean, default `false`
- `labels`: optional issue labels, default `["bug", "agent-discovered"]`

Output:

- Scan and filing summary
- Filed issue URLs
- Skipped duplicates
- Any scan or filing errors

Use this tool carefully. It creates real GitHub issues.

## Example Request

```json
{
  "tool": "discover_issues",
  "payload": {
    "github_token": "YOUR_TOKEN",
    "repository": "muthapriyanka/Prototype-Stackoverflow",
    "max_files": 100
  }
}
```

## Recommended Workflow

1. Run `discover_issues` first to preview findings.
2. Review the finding list.
3. Run `discover_and_file_issues` only when you want issues created on GitHub.
4. Use `issue_triage` or `create_issue_comment` for follow-up analysis on specific issues.
