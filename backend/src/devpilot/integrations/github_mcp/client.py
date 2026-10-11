"""GitHub integration using official hosted GitHub MCP server over HTTP.

Enables per-user token isolation: each client connects using the user's token.
"""

from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from devpilot.domain.issue import GitHubIssue


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


async def fetch_issue_via_mcp(
    mcp_client: MultiServerMCPClient,
    owner: str,
    repo: str,
    issue_number: int,
) -> GitHubIssue:
    """Invokes GitHub MCP 'get_issue' tool to retrieve normalized issue metadata."""
    tools = await mcp_client.get_tools()
    tool = next((t for t in tools if t.name == "get_issue"), None)
    if not tool:
        raise RuntimeError("GitHub MCP 'get_issue' tool not found on server.")

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
    """Directly invokes GitHub MCP 'create_pull_request' tool in PR Node without an extra LLM."""
    tools = await mcp_client.get_tools()
    tool = next((t for t in tools if t.name == "create_pull_request"), None)
    if not tool:
        raise RuntimeError("GitHub MCP 'create_pull_request' tool not found on server.")

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
