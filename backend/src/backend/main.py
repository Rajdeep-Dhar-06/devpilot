from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from backend.api.auth import router as github_auth_router
from backend.api.repositories import router as repositories_router
from backend.config import settings

app = FastAPI(title="DevPilot API")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="devpilot_session",
    same_site="lax",
    https_only=False,
)

app.include_router(github_auth_router)
app.include_router(repositories_router)

@app.get("/auth/me")
def get_current_user(request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(401, "User is not logged in")

    return {"user": user}


@app.get("/health")
def health():
    return {"status": "ok"}