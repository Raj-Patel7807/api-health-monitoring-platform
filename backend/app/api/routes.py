from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["infrastructure"])
def health() -> dict[str, str]:
    """Return process liveness without depending on external services."""

    return {"status": "ok"}
