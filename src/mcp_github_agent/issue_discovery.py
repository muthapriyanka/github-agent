from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Dict, List, Optional


AGENT_MARKER = "<!-- mcp-github-agent -->"
DEFAULT_LABELS = ["bug", "agent-discovered"]
SCAN_EXTENSIONS = (
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".css",
    ".md",
    ".java",
    ".xml",
    ".properties",
    ".yml",
    ".yaml",
)
EXCLUDED_PATH_PARTS = (
    "node_modules/",
    "dist/",
    "build/",
    "coverage/",
    ".git/",
    ".next/",
    "venv/",
    "__pycache__/",
)


@dataclass(frozen=True)
class IssueFinding:
    file_path: str
    category: str
    description: str
    evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def should_scan_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if any(part in normalized for part in EXCLUDED_PATH_PARTS):
        return False
    if normalized.endswith(("package-lock.json", "yarn.lock", "pnpm-lock.yaml")):
        return False
    return normalized.endswith(SCAN_EXTENSIONS)


def scan_content_for_issues(content: str, file_path: str) -> List[IssueFinding]:
    findings: List[IssueFinding] = []

    todos = re.findall(r"(TODO|FIXME|HACK|XXX):\s*(.+)", content)
    for tag, comment in todos:
        findings.append(IssueFinding(file_path, tag, comment.strip(), evidence=f"{tag}: {comment.strip()}"))

    if "setTimeout" in content and "clearTimeout" not in content:
        findings.append(IssueFinding(file_path, "Memory Leak", "setTimeout without clearTimeout cleanup"))

    if "setInterval" in content and "clearInterval" not in content:
        findings.append(IssueFinding(file_path, "Memory Leak", "setInterval without clearInterval cleanup"))

    if "console.log" in content:
        findings.append(IssueFinding(file_path, "Code Quality", "console.log statements should be removed for production"))

    if re.search(r"(password|secret|token|key)\s*[=:]\s*[\"']", content, re.IGNORECASE):
        findings.append(IssueFinding(file_path, "Security", "Potential hardcoded credentials or secrets"))

    if ".then(" in content and ".catch(" not in content:
        findings.append(IssueFinding(file_path, "Error Handling", "Promise chain without .catch() for error handling"))

    if "fetch(" in content and "loading" not in content.lower():
        findings.append(IssueFinding(file_path, "UI", "Network request without obvious loading state"))

    has_async_work = any(keyword in content for keyword in ["await ", ".then(", "fetch(", "axios"])
    if has_async_work and "try" not in content:
        findings.append(IssueFinding(file_path, "Error Handling", "Async work without explicit try/catch error handling"))

    if file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
        if re.search(r"\bany\b", content):
            findings.append(IssueFinding(file_path, "Type Safety", "Found 'any' usage"))

        if file_path.endswith((".js", ".jsx")) and "props" in content:
            findings.append(IssueFinding(file_path, "Typing", "React component props should be typed or documented"))

        if ".map(" in content and "FlatList" not in content:
            findings.append(IssueFinding(file_path, "Performance", "Long list rendering without virtualization"))

    if file_path.endswith(".json") and any(value in content for value in ["http://", "https://"]):
        findings.append(IssueFinding(file_path, "Configuration", "Hardcoded URL in JSON file"))

    comment_lines = len(re.findall(r"//.*", content))
    if comment_lines > 10:
        findings.append(IssueFinding(file_path, "Maintenance", f"Found {comment_lines} comment lines; review commented-out code"))

    return findings


def build_issue_title(finding: IssueFinding) -> str:
    title = f"[{finding.file_path}] {finding.category}: {finding.description}"
    return title[:120]


def build_issue_body(repository: str, finding: IssueFinding) -> str:
    lines = [
        AGENT_MARKER,
        "**Detected by MCP GitHub Agent**",
        "",
        f"Repository: `{repository}`",
        f"File: `{finding.file_path}`",
        f"Category: `{finding.category}`",
        "",
        f"Finding: {finding.description}",
    ]
    if finding.evidence:
        lines.extend(["", f"Evidence: `{finding.evidence}`"])
    lines.extend(["", "Recommended next step: review the file and apply a targeted fix."])
    return "\n".join(lines)


def build_analysis_comment(finding: IssueFinding, ai_analysis: Optional[str] = None) -> str:
    if ai_analysis:
        return f"**Autonomous Agent Analysis**\n\n{ai_analysis.strip()}"

    return (
        "**Autonomous Agent Analysis**\n\n"
        f"File: `{finding.file_path}`\n"
        f"Issue type: `{finding.category}`\n"
        f"Finding: {finding.description}\n\n"
        "Recommendation: verify the finding, add the smallest safe fix, and include a regression test when the behavior is user-facing."
    )


def summarize_findings(repository: str, scanned_files: int, findings: List[IssueFinding], limit: int = 20) -> str:
    lines = [
        f"Repository: {repository}",
        f"Scanned files: {scanned_files}",
        f"Findings: {len(findings)}",
    ]
    if not findings:
        lines.append("No issues detected by the current scan rules.")
        return "\n".join(lines)

    lines.append("")
    for index, finding in enumerate(findings[:limit], start=1):
        lines.append(f"{index}. [{finding.category}] {finding.file_path}: {finding.description}")

    remaining = len(findings) - limit
    if remaining > 0:
        lines.append(f"...and {remaining} more finding(s).")

    return "\n".join(lines)
