from fastapi import APIRouter

from app.auth.router import router as auth_router

router = APIRouter()
router.include_router(auth_router)


@router.get("/health", tags=["infrastructure"])
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""

    return {"status": "ok"}
