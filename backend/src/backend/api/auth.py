import secrets
from urllib.parse import urlencode
import httpx

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi import HTTPException

from backend.core.responses import success_response
from backend.integrations.github_app import get_installation_info
from backend.config import settings

from backend.db.models import User, Installation
from backend.db.session import SessionLocal


router = APIRouter(prefix="/auth/github", tags=["Github Login"])

@router.get("/login")
def github_login(request: Request):
    state = secrets.token_urlsafe(32)
    request.session["github_oauth_state"] = state
    
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_callback_url,
        "state": state
    }
    
    url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    
    return RedirectResponse(url, status_code=302)

@router.get("/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    expected_state = request.session.pop("github_oauth_state", None)
    
    if error:
        raise HTTPException(400, "Github Authorization was denied")
    
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    
    if not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(400, "Invalid Oauth state")
    
    async with httpx.AsyncClient(timeout=10) as http_client:
        token_response = await http_client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json"
            },
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
        )
        
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(502, "GitHub did not return an access token")
        
        user_response = await http_client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        
        user_response.raise_for_status()
        github_user = user_response.json()
        
        with SessionLocal() as db:
            db_user = (
                db.query(User)
                .filter(User.github_id == github_user["id"])
                .first()
            )

            if db_user is None:
                db_user = User(
                    github_id=github_user["id"],
                    login=github_user["login"],
                    avatar_url=github_user.get("avatar_url"),
                )
                db.add(db_user)
            else:
                db_user.login = github_user["login"]
                db_user.avatar_url = github_user.get("avatar_url")

            db.commit()
            db.refresh(db_user)

            user = {
                "id": db_user.id,
                "github_id": db_user.github_id,
                "login": db_user.login,
                "avatar_url": db_user.avatar_url,
            }

        request.session["user"] = user

        return {
            "success": True,
            "data": {"user": user},
            "error": None,
        }
                
@router.get("/install")
def github_install(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(
            "/auth/github/login",
            status_code=302
        )
        
    install_url = (
        f"https://github.com/apps/"
        f"{settings.github_app_slug}/installations/new"
    )
    
    return RedirectResponse(install_url, status_code=302)

@router.get("/setup")
async def github_setup(
    request: Request,
    installation_id: int,
    setup_action: str | None = None
):
    user = request.session.get("user")
    
    if not user:
        raise HTTPException(401, "Unauthorized")

    if setup_action not in {"install", "update"}:
        raise HTTPException(400, "Invalid installation action")
    
    installation = await get_installation_info(installation_id)
    
    if installation["app_id"] != int(settings.github_app_id):
        raise HTTPException(403, "Installation belongs to another app")
    
    account = installation.get("account", {})
    
    if account.get("id") != user["github_id"]:
        raise HTTPException(403, "Installation belongs to another account")

    with SessionLocal() as db:
        db_installation = (
            db.query(Installation)
            .filter(
                Installation.github_installation_id == installation["id"]
            )
            .first()
        )

        if db_installation is None:
            db_installation = Installation(
                user_id=user["id"],
                github_installation_id=installation["id"],
                account_id=account["id"],
                account_login=account["login"],
                repository_selection=installation["repository_selection"],
            )
            db.add(db_installation)
        else:
            db_installation.account_id = account["id"]
            db_installation.account_login = account["login"]
            db_installation.repository_selection = installation[
                "repository_selection"
            ]

        db.commit()
        db.refresh(db_installation)

    return success_response({
        "installation_id": installation["id"],
        "account_login": account["login"],
        "repository_selection": installation["repository_selection"],
    })
