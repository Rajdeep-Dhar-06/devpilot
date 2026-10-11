"""GitHub integration via GitHub MCP server and REST API.

Implements Decision 20:
- Uses langchain_mcp_adapters.client.MultiServerMCPClient for MCP tools.
- Containerized stdio transport invoking ghcr.io/github/github-mcp-server.
- Directly invokes create_pull_request tool in the PR Node without an extra LLM agent.
"""

from typing import Any

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from devpilot.core.exceptions import GitHubIntegrationError
from devpilot.domain.issue import GitHubIssue


def build_github_mcp_client(token: str) -> MultiServerMCPClient:
    """Builds a MultiServerMCPClient configured for the official GitHub MCP server.

    Runs ghcr.io/github/github-mcp-server inside a lightweight Docker container
    communicating over stdio.
    """
    return MultiServerMCPClient(
        {
            "github": {
                "transport": "stdio",
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "-e",
                    "GITHUB_TOOLS=create_pull_request",
                    "ghcr.io/github/github-mcp-server",
                ],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": token,
                },
            }
        }
    )


async def create_pull_request_via_mcp(
    mcp_client: MultiServerMCPClient,
    owner: str,
    repo: str,
    title: str,
    head_branch: str,
    base_branch: str = "main",
    body: str = "",
    draft: bool = False,
) -> str:
    """Directly invokes the create_pull_request MCP tool to publish a PR (Decision 20).

    Returns:
        The URL or identifier of the created pull request.
    """
    tools = await mcp_client.get_tools()
    create_pr_tool = next(
        (tool for tool in tools if tool.name == "create_pull_request"),
        None,
    )
    if create_pr_tool is None:
        raise GitHubIntegrationError("GitHub MCP tool 'create_pull_request' was not found.")

    payload: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "title": title,
        "head": head_branch,
        "base": base_branch,
        "body": body,
        "draft": draft,
    }

    try:
        result = await create_pr_tool.ainvoke(payload)
        # Parse result (URL or dict output)
        if isinstance(result, dict) and "html_url" in result:
            return str(result["html_url"])
        if isinstance(result, str) and result.startswith("http"):
            return result
        return str(result)
    except Exception as err:
        raise GitHubIntegrationError(f"GitHub MCP create_pull_request tool failed: {err}") from err


class GitHubClient:
    """Performs GitHub API operations using authenticated tokens."""

    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_issue(self, repo_slug: str, issue_number: int) -> GitHubIssue:
        """Retrieves and normalizes GitHub issue metadata."""
        url = f"{self.base_url}/repos/{repo_slug}/issues/{issue_number}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=self.headers)
                if resp.status_code != 200:
                    raise GitHubIntegrationError(
                        f"Failed fetching issue {repo_slug}#{issue_number} "
                        f"(status {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                labels = [label["name"] for label in data.get("labels", []) if "name" in label]
                return GitHubIssue(
                    issue_id=data["number"],
                    issue_url=data["html_url"],
                    title=data["title"],
                    description=data.get("body") or "",
                    repository=repo_slug,
                    labels=labels,
                )
        except Exception as err:
            if isinstance(err, GitHubIntegrationError):
                raise
            raise GitHubIntegrationError(f"HTTP request to get issue failed: {err}") from err

    def create_pull_request(
        self,
        repo_slug: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> str:
        """Creates a GitHub pull request and returns the resulting HTML URL."""
        url = f"{self.base_url}/repos/{repo_slug}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code != 201:
                    raise GitHubIntegrationError(
                        f"Failed creating PR for {repo_slug} "
                        f"(status {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                return str(data["html_url"])
        except Exception as err:
            if isinstance(err, GitHubIntegrationError):
                raise
            raise GitHubIntegrationError(f"HTTP request to create PR failed: {err}") from err
