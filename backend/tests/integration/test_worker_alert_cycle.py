"""Run the production Celery task routes against migrated PostgreSQL and a disposable broker."""

import asyncio
import json
import os
import time
from uuid import uuid4

import httpx
import pytest
from celery.contrib.testing.worker import start_worker
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import encrypt, generate_key
from app.db.models import Team, TeamMembership, TeamRole, User
from app.modules.alerts.hooks import unregister_b5_hooks
from app.modules.alerts.models import AlertDelivery
from app.modules.channels.models import NotificationChannel
from app.modules.incidents.models import Incident
from app.modules.monitors.checker import CheckResult
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult
from app.modules.team.service import update_team_member_role
from app.workers.celery_app import celery_app
from app.workers.tasks import run_health_check

pytestmark = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ, reason="requires a disposable migrated PostgreSQL database"
)


def test_worker_delivers_opening_and_recovery_once(monkeypatch):
    engine = create_engine(os.environ["DATABASE_URL"])
    team_id, monitor_id = uuid4(), uuid4()
    key = generate_key()
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    get_settings.cache_clear()
    outcomes = iter(["failing"] * 3 + ["healthy"] * 2)
    monkeypatch.setattr(
        "app.modules.monitors.checker.execute_http_check",
        lambda **_: CheckResult(str(monitor_id), next(outcomes)),
    )
    received = []

    def provider(request):
        received.append(json.loads(request.content)["text"])
        return httpx.Response(200)

    client_class = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: client_class(transport=httpx.MockTransport(provider), **kw)
    )
    try:
        with Session(engine) as db:
            db.execute(text("SELECT create_health_check_partition(CURRENT_DATE)"))
            db.add(Team(id=team_id, name=f"Alert regression {team_id}"))
            db.flush()
            db.add(
                Monitor(id=monitor_id, team_id=team_id, name="Payments", url="https://example.com")
            )
            db.add(
                NotificationChannel(
                    team_id=team_id,
                    type="slack",
                    name="Ops",
                    configuration={"test": True},
                    secret_ref=encrypt("https://hooks.slack.com/services/test", key=key),
                )
            )
            db.commit()

        unregister_b5_hooks()
        with start_worker(
            celery_app,
            pool="solo",
            queues=["monitoring", "notifications"],
            perform_ping_check=False,
            shutdown_timeout=20,
        ):
            for index in range(5):
                check_id = uuid4()
                with Session(engine) as db:
                    monitor = db.get(Monitor, monitor_id)
                    monitor.pending_check_id = check_id
                    db.commit()
                args = (str(monitor_id), str(check_id))
                assert run_health_check.delay(*args).get(timeout=15) == str(monitor_id)
                if index == 0:
                    assert run_health_check.delay(*args).get(timeout=15) == str(monitor_id)
            with Session(engine) as db:
                stmt = (
                    select(
                        AlertDelivery.event_type, AlertDelivery.status, AlertDelivery.attempt_count
                    )
                    .join(Incident)
                    .where(Incident.monitor_id == monitor_id)
                    .order_by(AlertDelivery.created_at)
                )
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    rows = db.execute(stmt).all()
                    if len(rows) == 2 and all(row.status == "sent" for row in rows):
                        break
                    time.sleep(0.05)
                assert rows == [("opened", "sent", 1), ("resolved", "sent", 1)]
                assert (
                    db.scalar(select(Incident.status).where(Incident.monitor_id == monitor_id))
                    == "resolved"
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(HealthCheckResult)
                        .where(HealthCheckResult.monitor_id == monitor_id)
                    )
                    == 5
                )
        assert [msg.split()[0] for msg in received] == ["[OPENED]", "[RESOLVED]"]
    finally:
        unregister_b5_hooks()
        get_settings.cache_clear()
        with engine.begin() as conn:
            conn.execute(delete(Team).where(Team.id == team_id))
        engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_demotions_preserve_last_admin():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg:", "postgresql+asyncpg:")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    team_id = uuid4()
    user_ids = [uuid4(), uuid4()]
    try:
        async with sessions.begin() as db:
            db.add(Team(id=team_id, name=f"Role regression {team_id}"))
            for uid in user_ids:
                db.add(
                    User(id=uid, email=f"{uid}@example.com", full_name="Test", password_hash="test")
                )
            await db.flush()
            db.add_all(
                [
                    TeamMembership(team_id=team_id, user_id=uid, role=TeamRole.admin)
                    for uid in user_ids
                ]
            )

        async def demote(uid):
            async with sessions() as db:
                try:
                    await update_team_member_role(db, team_id, uid, TeamRole.operator)
                    return 200
                except HTTPException as error:
                    return error.status_code

        assert sorted(await asyncio.gather(*(demote(uid) for uid in user_ids))) == [200, 409]
        async with sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(TeamMembership)
                    .where(TeamMembership.team_id == team_id, TeamMembership.role == TeamRole.admin)
                )
                == 1
            )
    finally:
        async with sessions.begin() as db:
            await db.execute(delete(Team).where(Team.id == team_id))
            await db.execute(delete(User).where(User.id.in_(user_ids)))
        await engine.dispose()
