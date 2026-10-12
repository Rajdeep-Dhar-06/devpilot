"""GitHub integration via remote GitHub MCP and GitHub App token authentication.

Beginner Guide:
1. Remote GitHub MCP (MultiServerMCPClient):
   Enables DevPilot to call GitHub's hosted tools (get_issue, create_pull_request)
   using the developer's personal or OAuth token directly over HTTP.
2. Short-lived GitHub App tokens:
   Mints temporary installation tokens for pushing branches securely.
"""

import time
from typing import Any

import httpx
import jwt
from langchain_mcp_adapters.client import MultiServerMCPClient

from devpilot.models import GitHubIssue


def get_github_mcp_client(
    token: str,
    endpoint_url: str = "https://api.githubcopilot.com/mcp/",
) -> MultiServerMCPClient:
    """Builds a per-user MultiServerMCPClient connected to the remote GitHub MCP endpoint."""
    connection: dict[str, Any] = {
        "transport": "http",
        "url": endpoint_url,
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }
    return MultiServerMCPClient({"github": connection})  # type: ignore[dict-item]


async def _get_mcp_tool(mcp_client: MultiServerMCPClient, tool_name: str) -> Any:
    """Helper to locate a specific tool on the remote MCP server."""
    tools = await mcp_client.get_tools()
    tool = next((t for t in tools if t.name == tool_name), None)
    if not tool:
        raise RuntimeError(f"GitHub MCP tool '{tool_name}' not found on server.")
    return tool


async def fetch_issue(
    mcp_client: MultiServerMCPClient,
    owner: str,
    repo: str,
    issue_number: int,
) -> GitHubIssue:
    """Fetches and normalizes an issue using the GitHub MCP 'get_issue' tool."""
    tool = await _get_mcp_tool(mcp_client, "get_issue")
    data = await tool.ainvoke({"owner": owner, "repo": repo, "issue_number": issue_number})

    labels = [lbl["name"] for lbl in data.get("labels", []) if "name" in lbl]

    return GitHubIssue(
        issue_id=data["number"],
        issue_url=data["html_url"],
        title=data["title"],
        description=data.get("body") or "",
        repository=f"{owner}/{repo}",
        labels=labels,
    )


async def create_pull_request(
    mcp_client: MultiServerMCPClient,
    owner: str,
    repo: str,
    title: str,
    head_branch: str,
    base_branch: str = "main",
    body: str = "",
    draft: bool = False,
) -> str:
    """Creates a pull request using the GitHub MCP 'create_pull_request' tool."""
    tool = await _get_mcp_tool(mcp_client, "create_pull_request")
    result = await tool.ainvoke(
        {
            "owner": owner,
            "repo": repo,
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
            "draft": draft,
        }
    )

    if isinstance(result, dict) and "html_url" in result:
        return str(result["html_url"])
    return str(result)


def generate_jwt_for_github_app(
    app_id: int,
    private_key_pem: str,
    expiration_seconds: int = 600,
) -> str:
    """Generates an RS256 JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,  # 60s in the past to allow for clock drift
        "exp": now + expiration_seconds,
        "iss": str(app_id),
    }
    token = jwt.encode(payload, private_key_pem, algorithm="RS256")
    return token if isinstance(token, str) else str(token.decode("utf-8"))


def mint_installation_access_token(
    app_id: int,
    private_key_pem: str,
    installation_id: int,
) -> str:
    """Mints a short-lived GitHub App installation token (Decision 11)."""
    app_jwt = generate_jwt_for_github_app(app_id, private_key_pem)
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers)
        resp.raise_for_status()
        return str(resp.json()["token"])
