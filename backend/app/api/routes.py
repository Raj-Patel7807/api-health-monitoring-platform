from fastapi import APIRouter

router = APIRouter()

# Existing health route
@router.get("/health", tags=["infrastructure"]) 
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""
    return {"status": "ok"}

# Include delivery and harness routers
from app.api.delivery_routes import router as delivery_router
from app.api.harness_routes import router as harness_router

router.include_router(delivery_router)
router.include_router(harness_router)
