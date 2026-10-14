from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.modules.monitors.router import router as monitors_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(monitors_router)


@router.get("/health", tags=["infrastructure"])
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""

    return {"status": "ok"}
