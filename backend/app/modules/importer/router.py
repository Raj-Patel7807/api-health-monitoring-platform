"""FastAPI router for API documentation import and monitor discovery."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.importer import service
from app.modules.importer.schemas import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
)
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_write,
)

router = APIRouter(prefix="/api/v1/monitors/import", tags=["monitor-importer"])

_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB limit


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_api_documentation_upload(
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    file: Annotated[
        UploadFile, File(description="API documentation file (Markdown, OpenAPI JSON or YAML)")
    ],
    base_url: Annotated[
        str | None, Form(description="Optional base URL to prepend to relative paths")
    ] = None,
) -> ImportPreviewResponse:
    """Upload an api.md or OpenAPI document, extract candidate endpoints, and return a preview."""
    filename = file.filename or "api.md"
    content_bytes = await file.read(_MAX_FILE_SIZE + 1)
    if len(content_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 2MB limit.",
        )

    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be valid UTF-8 text.",
        ) from None

    return service.preview_import_service(
        content=content_str,
        filename=filename,
        base_url=base_url,
    )


@router.post("/commit", response_model=ImportCommitResponse, status_code=status.HTTP_201_CREATED)
async def commit_imported_monitors(
    request: ImportCommitRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImportCommitResponse:
    """Commit selected discovered candidate endpoints into active monitors."""
    return await service.commit_import_service(
        db=db,
        team_id=context.team.id,
        request=request,
    )
