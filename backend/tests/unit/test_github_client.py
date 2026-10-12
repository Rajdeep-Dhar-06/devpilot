"""Unit tests for remote GitHub MCP client operations."""

from unittest.mock import AsyncMock

import pytest

from devpilot.github import (
    create_pull_request,
    fetch_issue,
    get_github_mcp_client,
)


def test_get_github_mcp_client_per_user() -> None:
    """Verifies that each user token receives an isolated client instance."""
    client_alice = get_github_mcp_client(token="token_alice")
    client_bob = get_github_mcp_client(token="token_bob")
    assert client_alice is not None
    assert client_bob is not None
    assert client_alice != client_bob


@pytest.mark.asyncio
async def test_fetch_issue_via_mcp() -> None:
    """Verifies that fetch_issue invokes the get_issue MCP tool and normalizes data."""
    mock_mcp = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "get_issue"
    mock_tool.ainvoke.return_value = {
        "number": 42,
        "html_url": "https://github.com/org/repo/issues/42",
        "title": "Fix division bug",
        "body": "ZeroDivisionError occurs",
        "labels": [{"name": "bug"}],
    }
    mock_mcp.get_tools.return_value = [mock_tool]

    issue = await fetch_issue(
        mcp_client=mock_mcp,
        owner="org",
        repo="repo",
        issue_number=42,
    )

    assert issue.issue_id == 42
    assert issue.title == "Fix division bug"
    assert issue.repository == "org/repo"
    assert issue.labels == ["bug"]
    mock_tool.ainvoke.assert_awaited_once_with({"owner": "org", "repo": "repo", "issue_number": 42})


@pytest.mark.asyncio
async def test_create_pull_request_via_mcp() -> None:
    """Verifies that create_pull_request invokes the MCP tool and extracts the PR URL."""
    mock_mcp = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "create_pull_request"
    mock_tool.ainvoke.return_value = {"html_url": "https://github.com/org/repo/pull/10"}
    mock_mcp.get_tools.return_value = [mock_tool]

    pr_url = await create_pull_request(
        mcp_client=mock_mcp,
        owner="org",
        repo="repo",
        title="Fix division bug",
        head_branch="devpilot/issue-42",
        base_branch="main",
        body="Closes #42",
    )

    assert pr_url == "https://github.com/org/repo/pull/10"
    mock_tool.ainvoke.assert_awaited_once_with(
        {
            "owner": "org",
            "repo": "repo",
            "title": "Fix division bug",
            "head": "devpilot/issue-42",
            "base": "main",
            "body": "Closes #42",
            "draft": False,
        }
    )
