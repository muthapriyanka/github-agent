from __future__ import annotations
from typing import Any, Dict


def issue_triage_prompt(issue: Dict[str, Any], repository: str) -> str:
    return (
        f"You are an autonomous engineering agent. Triage the GitHub issue below and provide:\n"
        f"1. Severity and priority.\n"
        f"2. Recommended labels.\n"
        f"3. Suggested next steps or a comment for the issue.\n"
        f"4. Any missing information required to proceed.\n\n"
        f"Repository: {repository}\n"
        f"Issue title: {issue.get('title')}\n"
        f"Issue body:\n{issue.get('body')}\n"
        f"Current labels: {issue.get('labels')}\n"
    )


def pr_review_prompt(pr: Dict[str, Any], changed_files: str, repository: str) -> str:
    return (
        f"You are an autonomous code review agent. Review the pull request and summarize findings.\n"
        f"1. Identify risk areas.\n"
        f"2. Suggest improvements or follow-up testing.\n"
        f"3. Recommend a review outcome (approve, request changes, comment).\n\n"
        f"Repository: {repository}\n"
        f"PR title: {pr.get('title')}\n"
        f"PR body:\n{pr.get('body')}\n"
        f"Changed files and diffs:\n{changed_files}\n"
    )


def code_summary_prompt(file_path: str, file_content: str, repository: str) -> str:
    return (
        f"Summarize the source file and explain the key responsibilities, public interfaces, and any potential areas for refactoring.\n"
        f"Repository: {repository}\n"
        f"File path: {file_path}\n"
        f"File content:\n{file_content}\n"
    )


def discovered_issue_analysis_prompt(finding: Dict[str, Any], code_excerpt: str, repository: str) -> str:
    return (
        f"You are an autonomous GitHub engineering agent. Explain the discovered code issue and recommend a concise fix.\n"
        f"Keep the answer practical and suitable for a GitHub issue comment.\n\n"
        f"Repository: {repository}\n"
        f"File path: {finding.get('file_path')}\n"
        f"Category: {finding.get('category')}\n"
        f"Finding: {finding.get('description')}\n"
        f"Evidence: {finding.get('evidence')}\n\n"
        f"Relevant code excerpt:\n{code_excerpt}\n"
    )
