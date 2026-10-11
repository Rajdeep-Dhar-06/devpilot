from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from devpilot.core.exceptions import GitHubIntegrationError
from devpilot.core.security import generate_jwt_for_github_app
from devpilot.integrations.github_mcp.client import (
    GitHubClient,
    build_github_mcp_client,
    create_pull_request_via_mcp,
)


def generate_dummy_private_key() -> str:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


def test_generate_jwt_for_github_app() -> None:
    pem_str = generate_dummy_private_key()
    token = generate_jwt_for_github_app(app_id=12345, private_key_pem=pem_str)
    assert isinstance(token, str)
    assert len(token) > 20


@patch("httpx.Client.get")
def test_fetch_issue(mock_get: MagicMock) -> None:
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "number": 42,
            "html_url": "https://github.com/org/repo/issues/42",
            "title": "Fix division",
            "body": "ZeroDivisionError occurs",
            "labels": [{"name": "bug"}],
        },
    )
    client = GitHubClient(token="dummy_token")
    issue = client.get_issue(repo_slug="org/repo", issue_number=42)
    assert issue.issue_id == 42
    assert issue.title == "Fix division"
    assert issue.labels == ["bug"]


@patch("httpx.Client.post")
def test_create_pull_request(mock_post: MagicMock) -> None:
    mock_post.return_value = MagicMock(
        status_code=201,
        json=lambda: {
            "html_url": "https://github.com/org/repo/pull/10",
        },
    )
    client = GitHubClient(token="dummy_token")
    pr_url = client.create_pull_request(
        repo_slug="org/repo",
        title="Fix division bug",
        body="Resolves #42",
        head_branch="devpilot/issue-42",
        base_branch="main",
    )
    assert pr_url == "https://github.com/org/repo/pull/10"


def test_build_github_mcp_client() -> None:
    client = build_github_mcp_client(token="ghs_test123")
    assert client is not None


@pytest.mark.asyncio
async def test_create_pull_request_via_mcp_success() -> None:
    mock_mcp = AsyncMock()
    mock_tool = AsyncMock()
    mock_tool.name = "create_pull_request"
    mock_tool.ainvoke.return_value = {"html_url": "https://github.com/org/repo/pull/99"}
    mock_mcp.get_tools.return_value = [mock_tool]

    pr_url = await create_pull_request_via_mcp(
        mcp_client=mock_mcp,
        owner="org",
        repo="repo",
        title="Fix: division bug",
        head_branch="devpilot/issue-42",
        base_branch="main",
        body="Summary of changes",
    )
    assert pr_url == "https://github.com/org/repo/pull/99"
    mock_tool.ainvoke.assert_awaited_once_with(
        {
            "owner": "org",
            "repo": "repo",
            "title": "Fix: division bug",
            "head": "devpilot/issue-42",
            "base": "main",
            "body": "Summary of changes",
            "draft": False,
        }
    )


@pytest.mark.asyncio
async def test_create_pull_request_via_mcp_missing_tool() -> None:
    mock_mcp = AsyncMock()
    mock_mcp.get_tools.return_value = []

    with pytest.raises(GitHubIntegrationError, match="tool 'create_pull_request' was not found"):
        await create_pull_request_via_mcp(
            mcp_client=mock_mcp,
            owner="org",
            repo="repo",
            title="Fix",
            head_branch="devpilot/fix",
        )
