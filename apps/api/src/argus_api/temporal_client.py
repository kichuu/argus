from temporalio.client import Client

from argus_core.logging import get_logger
from argus_core.settings import get_settings

logger = get_logger(__name__)


class TemporalUnavailableError(RuntimeError):
    pass


async def get_client() -> Client:
    settings = get_settings()
    try:
        return await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    except Exception as exc:
        logger.warning(
            "temporal.connect_failed",
            host=settings.temporal_host,
            namespace=settings.temporal_namespace,
            error=str(exc),
        )
        raise TemporalUnavailableError(str(exc)) from exc
