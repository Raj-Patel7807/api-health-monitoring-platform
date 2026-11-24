"""FastAPI router for Monitor CRUD and health-check results."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamMembership, TeamRole
from app.db.session import get_db
from app.integrations.llm.extractor import extract_endpoints_from_markdown
from app.modules.dashboard.service import get_monitor_health
from app.modules.monitors import service
from app.modules.monitors.dependencies import (
    TeamContext,
    require_admin,
    require_monitor_read,
    require_monitor_write,
)
from app.modules.monitors.schemas import (
    ExtractedEndpointItem,
    MarkdownExtractRequest,
    MarkdownExtractResponse,
    MonitorBatchCreateRequest,
    MonitorBatchCreateResponse,
    MonitorCreateRequest,
    MonitorDetailResponse,
    MonitorListResponse,
    MonitorResponse,
    MonitorUpdateRequest,
)
from app.modules.results import service as results_service
from app.modules.results.schemas import (
    HealthCheckResultResponse,
    HealthCheckResultsResponse,
)

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])


@router.post(
    "",
    response_model=MonitorDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitor(
    body: MonitorCreateRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Register and configure a new API endpoint monitor under the active team."""
    effective_team_id = context.team.id
    if body.team_id is not None and body.team_id != context.team.id:
        stmt = select(TeamMembership).where(
            TeamMembership.team_id == body.team_id,
            TeamMembership.user_id == context.user.id,
            TeamMembership.role.in_([TeamRole.admin, TeamRole.operator]),
        )
        membership = (await db.execute(stmt)).scalar_one_or_none()
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create monitors for the specified team.",
            )
        effective_team_id = body.team_id

    monitor = await service.create_monitor(db, effective_team_id, body)
    return MonitorDetailResponse.model_validate(monitor)


@router.get("", response_model=MonitorListResponse)
async def list_monitors(
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> MonitorListResponse:
    """List active monitors belonging to the caller's team."""
    items, total = await service.list_monitors(
        db=db,
        team_id=context.team.id,
        page=page,
        page_size=page_size,
    )
    return MonitorListResponse(
        items=[MonitorResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{id}", response_model=MonitorDetailResponse)
async def get_monitor(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Retrieve full configuration and current health state for a single monitor."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    detail = MonitorDetailResponse.model_validate(monitor)
    detail.health_status = await get_monitor_health(db, monitor.id)
    return detail


@router.get(
    "/{monitor_id}/results",
    response_model=HealthCheckResultsResponse,
)
async def get_monitor_results(
    monitor_id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    result_status: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HealthCheckResultsResponse:
    """Get paginated health-check results for a monitor owned by the caller's team."""

    monitor = await service.get_monitor(
        db,
        context.team.id,
        monitor_id,
    )

    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )

    items, total, effective_start, effective_end = await results_service.list_health_check_results(
        db=db,
        monitor_id=monitor_id,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        result_status=result_status,
    )

    return HealthCheckResultsResponse(
        items=[HealthCheckResultResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        start_time=effective_start,
        end_time=effective_end,
    )


@router.patch("/{id}", response_model=MonitorDetailResponse)
async def update_monitor(
    id: UUID,
    body: MonitorUpdateRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Partially update an existing monitor."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    updated = await service.update_monitor(db, monitor, body)
    detail = MonitorDetailResponse.model_validate(updated)
    detail.health_status = await get_monitor_health(db, updated.id)
    return detail


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a monitor by setting deleted_at and disabling it."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    await service.soft_delete_monitor(db, monitor)


@router.post(
    "/ai-extract",
    response_model=MarkdownExtractResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_monitors_from_markdown(
    body: MarkdownExtractRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
) -> MarkdownExtractResponse:
    """Use Gemini Flash Lite (or heuristic fallback) to parse markdown endpoints."""
    result = await extract_endpoints_from_markdown(
        markdown_content=body.markdown_content,
        base_url=body.base_url,
    )
    items = [
        ExtractedEndpointItem(
            name=ep.name,
            method=ep.method,
            url=ep.url,
            expected_status_code=ep.expected_status_code,
            timeout_seconds=ep.timeout_seconds,
            check_interval_seconds=ep.check_interval_seconds,
            failure_threshold=ep.failure_threshold,
            recovery_threshold=ep.recovery_threshold,
            description=ep.description,
        )
        for ep in result.endpoints
    ]
    return MarkdownExtractResponse(
        endpoints=items,
        total_found=result.total_found,
        warnings=result.warnings,
        used_llm=result.used_llm,
    )


@router.post(
    "/batch",
    response_model=MonitorBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitors_batch(
    body: MonitorBatchCreateRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorBatchCreateResponse:
    """Batch register multiple API endpoint monitors under the active team."""
    created = await service.create_monitors_batch(
        db=db,
        team_id=context.team.id,
        monitors_data=body.monitors,
    )
    return MonitorBatchCreateResponse(
        created=[MonitorDetailResponse.model_validate(m) for m in created],
        count=len(created),
    )
