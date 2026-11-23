from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.modules.ai.router import router as ai_router
from app.modules.channels.router import router as channels_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.importer.router import router as importer_router
from app.modules.incidents.router import router as incidents_router
from app.modules.monitors.router import router as monitors_router
from app.modules.team.router import router as team_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(incidents_router)
router.include_router(monitors_router)
router.include_router(importer_router)
router.include_router(ai_router)
router.include_router(channels_router)
router.include_router(dashboard_router)
router.include_router(team_router)


# Existing health route
@router.get("/health", tags=["infrastructure"])
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""
    return {"status": "ok"}
