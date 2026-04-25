from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from argus_core.logging import configure_logging, get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argus_api import __version__
from argus_api.ingest_scheduler import get_scheduler, maybe_start_scheduler
from argus_api.routes import (
    claims,
    config,
    discussions,
    entities,
    health,
    metrics,
    personas,
    sources,
    suggested,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("argus_api.startup", version=__version__)
    await maybe_start_scheduler()
    try:
        yield
    finally:
        await get_scheduler().stop()
        logger.info("argus_api.shutdown")


app = FastAPI(
    title="Argus API",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(claims.router)
app.include_router(entities.router)
app.include_router(sources.router)
app.include_router(discussions.router)
app.include_router(personas.router)
app.include_router(suggested.router)
app.include_router(config.router)
app.include_router(metrics.router)
