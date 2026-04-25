import asyncio

from argus_core.instrumentation import setup_telemetry
from argus_core.logging import configure_logging, get_logger
from argus_core.settings import get_settings
from temporalio.client import Client
from temporalio.worker import Worker

from argus_workers.activities.discussion import (
    _mark_failed,
    assemble_evidence_pack,
    persist_results,
    run_discussion_graph,
    start_discussion,
)
from argus_workers.activities.extract import extract_claims
from argus_workers.activities.fetch import fetch_source, index_evidence
from argus_workers.activities.verify import verify_claims
from argus_workers.workflows.discussion import DiscussionWorkflow
from argus_workers.workflows.ingestion import IngestionWorkflow

logger = get_logger(__name__)


async def run_worker() -> None:
    configure_logging()
    setup_telemetry("argus-workers")
    settings = get_settings()

    logger.info(
        "argus_workers.connecting",
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
    )
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[IngestionWorkflow, DiscussionWorkflow],
        activities=[
            fetch_source,
            extract_claims,
            verify_claims,
            index_evidence,
            start_discussion,
            assemble_evidence_pack,
            run_discussion_graph,
            persist_results,
            _mark_failed,
        ],
    )

    logger.info("argus_workers.started")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
