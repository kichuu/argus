from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argus_core.logging import configure_logging, get_logger

from argus_api import __version__
from argus_api.routes import claims, discussions, entities, health, sources

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("argus_api.startup", version=__version__)
    yield
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
