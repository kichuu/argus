from typing import Annotated

from argus_core.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api import __version__
from argus_api.deps import get_session

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
