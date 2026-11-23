"""Service functions for API documentation import and monitor batch creation."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.importer.parser import parse_api_documentation
from app.modules.importer.schemas import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
)
from app.modules.importer.ssrf import is_safe_url
from app.modules.monitors.models import Monitor

logger = logging.getLogger(__name__)


def preview_import_service(
    content: str,
    filename: str,
    base_url: str | None = None,
) -> ImportPreviewResponse:
    """Extract candidate monitors and return a preview."""
    candidates = parse_api_documentation(
        content=content,
        filename=filename,
        default_base_url=base_url,
    )
    valid_count = sum(1 for c in candidates if c.is_valid)
    return ImportPreviewResponse(
        filename=filename,
        total_found=len(candidates),
        valid_count=valid_count,
        items=candidates,
    )


async def commit_import_service(
    db: AsyncSession,
    team_id: UUID,
    request: ImportCommitRequest,
) -> ImportCommitResponse:
    """Persist selected candidate monitors to the database under the caller's team."""
    if not request.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate monitors provided for import.",
        )

    created_ids: list[UUID] = []
    base_url = (request.base_url or "").rstrip("/")

    for item in request.items:
        url = item.url.strip()
        if url.startswith("/") and base_url:
            url = f"{base_url}/{url.lstrip('/')}"

        # Strict security validation before committing to DB
        is_safe, error = is_safe_url(url, allow_relative=False)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot import monitor '{item.name}': {error}",
            )

        monitor = Monitor(
            id=uuid4(),
            team_id=team_id,
            name=item.name[:150],
            url=url,
            method=item.method,
            enabled=True,
            check_interval_seconds=item.check_interval_seconds,
            current_interval_seconds=item.check_interval_seconds,
            timeout_seconds=item.timeout_seconds,
            failure_threshold=item.failure_threshold,
            recovery_threshold=item.recovery_threshold,
            expected_status_code=item.expected_status_code,
        )
        db.add(monitor)
        created_ids.append(monitor.id)

    await db.commit()
    logger.info("Successfully imported %d monitors for team %s", len(created_ids), team_id)

    return ImportCommitResponse(
        imported_count=len(created_ids),
        monitor_ids=created_ids,
    )
