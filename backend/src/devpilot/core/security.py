"""Security utilities for GitHub App authentication and token minting (Decision 11)."""

import time

import httpx
import jwt

from devpilot.core.exceptions import GitHubIntegrationError


def generate_jwt_for_github_app(
    app_id: int,
    private_key_pem: str,
    expiration_seconds: int = 600,
) -> str:
    """Generates an RS256 JWT for GitHub App authentication.

    Args:
        app_id: GitHub App identifier.
        private_key_pem: Private key in PEM format.
        expiration_seconds: Lifetime of the JWT in seconds (max 10 minutes).

    Returns:
        Encoded RS256 JWT string.
    """
    now = int(time.time())
    payload = {
        # Issued at time (60 seconds in the past to allow for clock drift)
        "iat": now - 60,
        # JWT expiration time (10 minutes maximum)
        "exp": now + expiration_seconds,
        # GitHub App's identifier
        "iss": str(app_id),
    }

    try:
        token = jwt.encode(payload, private_key_pem, algorithm="RS256")
        return token if isinstance(token, str) else token.decode("utf-8")
    except Exception as err:
        raise GitHubIntegrationError(f"Failed to generate GitHub App JWT: {err}") from err


def mint_installation_access_token(
    app_id: int,
    private_key_pem: str,
    installation_id: int,
) -> str:
    """Mints a short-lived GitHub App installation token.

    Args:
        app_id: GitHub App identifier.
        private_key_pem: Private key in PEM format.
        installation_id: Specific installation identifier.

    Returns:
        Short-lived GitHub installation access token string.
    """
    app_jwt = generate_jwt_for_github_app(app_id=app_id, private_key_pem=private_key_pem)
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers)
            if resp.status_code != 201:
                raise GitHubIntegrationError(
                    f"GitHub API error minting installation token "
                    f"(status {resp.status_code}): {resp.text}"
                )
            data = resp.json()
            return str(data["token"])
    except Exception as err:
        if isinstance(err, GitHubIntegrationError):
            raise
        raise GitHubIntegrationError(
            f"HTTP request to mint installation token failed: {err}"
        ) from err
