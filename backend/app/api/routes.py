from fastapi import APIRouter

from app.api.delivery_routes import router as delivery_router
from app.api.harness_routes import router as harness_router
from app.auth.router import router as auth_router
from app.modules.channels.router import router as channels_router
from app.modules.monitors.router import router as monitors_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(monitors_router)
router.include_router(channels_router)


# Existing health route
@router.get("/health", tags=["infrastructure"])
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""
    return {"status": "ok"}


router.include_router(delivery_router)
router.include_router(harness_router)
