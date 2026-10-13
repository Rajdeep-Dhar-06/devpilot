import time
from pathlib import Path

import httpx 

import jwt

from backend.config import settings

def create_app_jwt() -> str:
    private_key = Path(settings.github_private_key_path).read_text(encoding="utf-8")
    
    now = int(time.time())
    
    payload = {
        "iat": now - 60,
        "exp": now + 50,
        "iss": settings.github_client_id
    }
    
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )
    
async def get_app_info() -> dict:
    app_jwt = create_app_jwt()
    
    async with httpx.AsyncClient(timeout=10) as http_client:
        response = await http_client.get(
            f"https://api.github.com/app",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        
        response.raise_for_status()
        return response.json()
    
async def get_installation_info(installation_id: int) -> dict:
    app_jwt = create_app_jwt()

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        response.raise_for_status()
        return response.json()

async def create_installation_token(installation_id: int) -> str:
    app_jwt = create_app_jwt()

    async with httpx.AsyncClient(timeout=10) as http_client:
        response = await http_client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        response.raise_for_status()
        token_data = response.json()

    return token_data["token"]

async def list_installation_repositories(installation_id: int) -> list[dict]:
    token = await create_installation_token(installation_id)

    async with httpx.AsyncClient(timeout=10) as http_client:
        response = await http_client.get(
            "https://api.github.com/installation/repositories",
            params={"per_page": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        response.raise_for_status()
        result = response.json()

    return [
        {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "private": repo["private"],
            "html_url": repo["html_url"],
            "default_branch": repo.get("default_branch"),
        }
        for repo in result["repositories"]
    ]