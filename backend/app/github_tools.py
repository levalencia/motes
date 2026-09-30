"""GitHub tools — list repos, list issues, create issues via GitHub REST API.

Uses GITHUB_TOKEN env var for authentication.
"""

from __future__ import annotations

import json
import os

import httpx
import structlog

from app.tools import Tool

logger = structlog.get_logger()

GITHUB_API = "https://api.github.com"


def _github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MotesAssistant/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


class GitHubListReposTool(Tool):
    """List GitHub repositories for a user or the authenticated user."""

    name = "github_list_repos"
    description = (
        "List GitHub repositories for a user or the authenticated user. "
        "Returns repo names, descriptions, stars, and languages. "
        "Requires GITHUB_TOKEN env var for private repos."
    )
    parameters = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "GitHub username (omit for authenticated user's repos)",
            },
            "sort": {
                "type": "string",
                "enum": ["updated", "created", "pushed", "full_name"],
                "description": "Sort order (default: updated)",
            },
            "limit": {
                "type": "integer",
                "description": "Max repos to return (default: 10)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict) -> str:
        username = arguments.get("username")
        sort = arguments.get("sort", "updated")
        limit = arguments.get("limit", 10)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = f"{GITHUB_API}/users/{username}/repos" if username else f"{GITHUB_API}/user/repos"

                resp = await client.get(
                    url,
                    params={"sort": sort, "per_page": min(limit, 100), "direction": "desc"},
                    headers=_github_headers(),
                )
                resp.raise_for_status()
                repos = []
                for repo in resp.json()[:limit]:
                    repos.append({
                        "name": repo.get("full_name"),
                        "description": repo.get("description"),
                        "stars": repo.get("stargazers_count"),
                        "language": repo.get("language"),
                        "url": repo.get("html_url"),
                        "private": repo.get("private"),
                        "updated_at": repo.get("updated_at"),
                    })
                return json.dumps({"repos": repos, "count": len(repos)})
        except Exception as e:
            logger.warning("github_list_repos_error", error=str(e))
            return json.dumps({"error": str(e)})


class GitHubListIssuesTool(Tool):
    """List issues for a GitHub repository."""

    name = "github_list_issues"
    description = (
        "List issues for a GitHub repository. "
        "Returns issue titles, states, labels, and assignees."
    )
    parameters = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format (e.g., 'facebook/react')",
            },
            "state": {
                "type": "string",
                "enum": ["open", "closed", "all"],
                "description": "Filter by state (default: open)",
            },
            "limit": {
                "type": "integer",
                "description": "Max issues to return (default: 10)",
            },
        },
        "required": ["repo"],
    }

    async def execute(self, arguments: dict) -> str:
        repo = arguments.get("repo", "")
        state = arguments.get("state", "open")
        limit = arguments.get("limit", 10)

        if not repo or "/" not in repo:
            return json.dumps({"error": "repo must be in 'owner/repo' format"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{GITHUB_API}/repos/{repo}/issues",
                    params={"state": state, "per_page": min(limit, 100)},
                    headers=_github_headers(),
                )
                resp.raise_for_status()
                issues = []
                for issue in resp.json()[:limit]:
                    if issue.get("pull_request"):
                        continue  # Skip PRs
                    issues.append({
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "labels": [lb.get("name") for lb in issue.get("labels", [])],
                        "assignees": [a.get("login") for a in issue.get("assignees", [])],
                        "created_at": issue.get("created_at"),
                        "url": issue.get("html_url"),
                    })
                return json.dumps({"issues": issues, "count": len(issues)})
        except Exception as e:
            logger.warning("github_list_issues_error", error=str(e))
            return json.dumps({"error": str(e)})


class GitHubCreateIssueTool(Tool):
    """Create a new issue in a GitHub repository."""

    name = "github_create_issue"
    description = (
        "Create a new issue in a GitHub repository. "
        "Requires GITHUB_TOKEN env var with repo write access."
    )
    parameters = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format",
            },
            "title": {
                "type": "string",
                "description": "Issue title",
            },
            "body": {
                "type": "string",
                "description": "Issue body/description (Markdown supported)",
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels to apply (e.g., ['bug', 'urgent'])",
            },
        },
        "required": ["repo", "title"],
    }

    async def execute(self, arguments: dict) -> str:
        repo = arguments.get("repo", "")
        title = arguments.get("title", "")
        body = arguments.get("body", "")
        labels = arguments.get("labels", [])

        if not repo or "/" not in repo:
            return json.dumps({"error": "repo must be in 'owner/repo' format"})
        if not title:
            return json.dumps({"error": "title is required"})
        if not os.environ.get("GITHUB_TOKEN"):
            return json.dumps({"error": "GITHUB_TOKEN env var is required to create issues"})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {"title": title}
                if body:
                    payload["body"] = body
                if labels:
                    payload["labels"] = labels

                resp = await client.post(
                    f"{GITHUB_API}/repos/{repo}/issues",
                    json=payload,
                    headers=_github_headers(),
                )
                resp.raise_for_status()
                issue = resp.json()
                return json.dumps({
                    "created": True,
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "url": issue.get("html_url"),
                })
        except Exception as e:
            logger.warning("github_create_issue_error", error=str(e))
            return json.dumps({"error": str(e)})
