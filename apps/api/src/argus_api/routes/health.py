from datetime import UTC, datetime, timedelta
from typing import Annotated

from argus_core.db.models import (
    ClaimModel,
    DiscussionRunModel,
    EntityModel,
    SourceModel,
)
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.settings import get_settings
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api import __version__
from argus_api.deps import get_session
from argus_api.ingest_scheduler import get_scheduler

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/db")
async def health_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
    except Exception as exc:
        logger.warning("health_db.failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unreachable",
        ) from exc
    return {"status": "ok"}


# --- /health/system -----------------------------------------------------------


class SchedulerStatus(BaseModel):
    running: bool
    interval_seconds: int


class DbStatus(BaseModel):
    claims_total: int
    claims_24h: int
    sources_total: int
    sources_24h: int
    entities_total: int
    discussions_total: int
    discussions_running: int


class QdrantStatus(BaseModel):
    collection: str
    points_count: int | None
    available: bool


class AgeStatus(BaseModel):
    graph: str
    node_count: int | None
    available: bool


class SystemStatus(BaseModel):
    api_version: str
    scheduler: SchedulerStatus
    db: DbStatus
    qdrant: QdrantStatus
    age: AgeStatus
    last_ingest_at: datetime | None


_RUNNING_STATUSES = ("planning", "researching", "debating")


async def _collect_db_status() -> tuple[DbStatus, datetime | None]:
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    async with session_scope() as session:
        claims_total = int(
            (await session.execute(select(func.count()).select_from(ClaimModel)))
            .scalar_one()
            or 0
        )
        claims_24h = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(ClaimModel)
                    .where(ClaimModel.created_at >= cutoff)
                )
            ).scalar_one()
            or 0
        )
        sources_total = int(
            (await session.execute(select(func.count()).select_from(SourceModel)))
            .scalar_one()
            or 0
        )
        sources_24h = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(SourceModel)
                    .where(SourceModel.fetched_at >= cutoff)
                )
            ).scalar_one()
            or 0
        )
        entities_total = int(
            (await session.execute(select(func.count()).select_from(EntityModel)))
            .scalar_one()
            or 0
        )
        discussions_total = int(
            (await session.execute(select(func.count()).select_from(DiscussionRunModel)))
            .scalar_one()
            or 0
        )
        discussions_running = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(DiscussionRunModel)
                    .where(DiscussionRunModel.status.in_(_RUNNING_STATUSES))
                )
            ).scalar_one()
            or 0
        )
        last_ingest_at = (
            await session.execute(select(func.max(SourceModel.fetched_at)))
        ).scalar_one()

    db_status = DbStatus(
        claims_total=claims_total,
        claims_24h=claims_24h,
        sources_total=sources_total,
        sources_24h=sources_24h,
        entities_total=entities_total,
        discussions_total=discussions_total,
        discussions_running=discussions_running,
    )
    return db_status, last_ingest_at


async def _collect_qdrant_status() -> QdrantStatus:
    settings = get_settings()
    collection = settings.qdrant_collection_evidence
    try:
        # Local import keeps the route importable when qdrant_client is not
        # installed in some test environments.
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            check_compatibility=False,
        )
        info = await client.get_collection(collection)
        points = getattr(info, "points_count", None)
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            pass
        return QdrantStatus(
            collection=collection,
            points_count=int(points) if points is not None else 0,
            available=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_system.qdrant_failed", error=str(exc))
        return QdrantStatus(collection=collection, points_count=None, available=False)


async def _collect_age_status() -> AgeStatus:
    # Lazy import for the same reason as qdrant; also lets tests monkeypatch.
    try:
        from argus_retrieval.graph import GRAPH_NAME, GraphQuerier
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_system.age_import_failed", error=str(exc))
        return AgeStatus(graph="argus_graph", node_count=None, available=False)

    graph_name = GRAPH_NAME
    try:
        querier = GraphQuerier(graph_name)
        rows = await querier._exec_cypher(
            "MATCH (n) RETURN count(n)", return_cols="(c agtype)"
        )
        count: int | None = None
        if rows:
            raw = rows[0][0]
            try:
                # agtype scalar comes back as a string like '0' or '0::int'.
                s = str(raw).strip().strip('"')
                if "::" in s:
                    s = s.split("::", 1)[0]
                count = int(s)
            except (TypeError, ValueError):
                count = None
        return AgeStatus(graph=graph_name, node_count=count, available=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_system.age_failed", error=str(exc))
        return AgeStatus(graph=graph_name, node_count=None, available=False)


@router.get("/health/system", response_model=SystemStatus)
async def health_system() -> SystemStatus:
    settings = get_settings()
    scheduler = SchedulerStatus(
        running=get_scheduler().is_running(),
        interval_seconds=settings.ingest_interval_seconds,
    )
    db_status, last_ingest_at = await _collect_db_status()
    qdrant_status = await _collect_qdrant_status()
    age_status = await _collect_age_status()

    return SystemStatus(
        api_version=__version__,
        scheduler=scheduler,
        db=db_status,
        qdrant=qdrant_status,
        age=age_status,
        last_ingest_at=last_ingest_at,
    )
