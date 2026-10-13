from fastapi import APIRouter, HTTPException, Request

from backend.core.responses import success_response
from backend.db.models import Installation, Repository
from backend.db.session import SessionLocal
from backend.integrations.github_app import list_installation_repositories


router = APIRouter(prefix="/api", tags=["repositories"])

@router.get("/repositories")
async def get_repositories(request: Request):
    user = request.session.get("user")
    
    if not user or not user.get("id"):
        raise HTTPException(401, "Unauthorized")
    
    with SessionLocal() as db:
        repositories = (
            db.query(Repository)
            .join(Installation)
            .filter(Installation.user_id == user["id"])
            .order_by(Repository.full_name)
            .all()
        )

        result = [
            {
                "id": repo.id,
                "github_repo_id": repo.github_repo_id,
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "html_url": repo.html_url,
                "default_branch": repo.default_branch,
            }
            for repo in repositories
        ]

    return success_response({"repositories": result})
    
@router.post("/repositories/sync")
async def sync_repositories(request: Request):
    user = request.session.get("user")
    
    if not user or not user.get("id"):
        raise HTTPException(401, "Unauthorized")
    
    with SessionLocal() as db:
        installations = (
            db.query(Installation)
            .filter(Installation.user_id == user["id"])
            .all()
        )
        
        installation_refs = [
            (item.id, item.github_installation_id)
            for item in installations
        ]
        
        if not installation_refs:
            raise HTTPException(409, "No GitHub App installation connected")
            
        remote_repositories = []

        for internal_id, github_id in installation_refs:
            repositories = await list_installation_repositories(github_id)

            for repo in repositories:
                remote_repositories.append((internal_id, repo))

        synced = []

        with SessionLocal() as db:
            for internal_installation_id, repo in remote_repositories:
                db_repo = (
                    db.query(Repository)
                    .filter(Repository.github_repo_id == repo["id"])
                    .first()
                )

                if db_repo is None:
                    db_repo = Repository(
                        github_repo_id=repo["id"],
                        installation_id=internal_installation_id,
                        name=repo["name"],
                        full_name=repo["full_name"],
                        private=repo["private"],
                        html_url=repo["html_url"],
                        default_branch=repo.get("default_branch"),
                    )
                    db.add(db_repo)
                else:
                    db_repo.installation_id = internal_installation_id
                    db_repo.name = repo["name"]
                    db_repo.full_name = repo["full_name"]
                    db_repo.private = repo["private"]
                    db_repo.html_url = repo["html_url"]
                    db_repo.default_branch = repo.get("default_branch")

                db.flush()

                synced.append({
                    "id": db_repo.id,
                    "github_repo_id": db_repo.github_repo_id,
                    "full_name": db_repo.full_name,
                    "private": db_repo.private,
                })

            db.commit()

    return success_response({
        "repositories": synced,
        "count": len(synced),
    })