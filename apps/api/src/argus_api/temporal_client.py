"""Submission layer for kicking off Argus discussions.

Two modes:
- Temporal-backed (production): connect to the Temporal frontend and start
  the ``DiscussionWorkflow``. The workflow ID is ``discussion-{discussion_id}``.
- Local fallback (dev): when Temporal is unreachable, run the activity
  functions directly as a background asyncio task. The HTTP request still
  returns immediately with the discussion_id so the frontend can poll.

The launcher never blocks the request on workflow completion. Either path
is fire-and-forget from the API's perspective.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from argus_core.logging import get_logger
from argus_core.settings import get_settings
from temporalio.client import Client

logger = get_logger(__name__)


class TemporalUnavailableError(RuntimeError):
    pass


_CONNECT_TIMEOUT_SECONDS = 3.0

# Hold strong references to background tasks so the event loop GC doesn't
# kill them mid-flight. Tasks remove themselves on completion.
_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()


def _spawn_background(coro: Any) -> None:
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def _connect_with_timeout() -> Client:
    """Connect to Temporal with a short timeout. Raises on any failure."""
    settings = get_settings()
    return await asyncio.wait_for(
        Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        ),
        timeout=_CONNECT_TIMEOUT_SECONDS,
    )


async def get_client() -> Client:
    """Backward-compatible accessor. Prefer ``DiscussionLauncher`` for new code."""
    try:
        return await _connect_with_timeout()
    except (TimeoutError, ConnectionError, OSError) as exc:
        logger.warning("temporal.connect_failed", error=str(exc))
        raise TemporalUnavailableError(str(exc)) from exc
    except Exception as exc:
        logger.warning("temporal.connect_failed", error=str(exc))
        raise TemporalUnavailableError(str(exc)) from exc


async def _run_activities_directly(topic: str, vertical: str, discussion_id: str) -> None:
    """Dev fallback: invoke the discussion activity functions sequentially.

    Mirrors the workflow in ``apps/workers/.../workflows/discussion.py``. Any
    exception is logged; we mark the row as failed so the frontend can show
    something useful.
    """
    from argus_workers.activities.discussion import (
        assemble_evidence_pack,
        persist_results,
        run_discussion_graph,
        start_discussion,
    )

    try:
        did = await start_discussion(topic, vertical, discussion_id)
        await assemble_evidence_pack(did)
        graph_result: dict[str, Any] = await run_discussion_graph(did)
        await persist_results(did, graph_result)
        logger.info("discussion.local_pipeline.done", discussion_id=did)
    except Exception as exc:
        logger.exception(
            "discussion.local_pipeline.failed",
            discussion_id=discussion_id,
            error=str(exc),
        )
        await _mark_failed(discussion_id, str(exc))


async def _mark_failed(discussion_id: str, error: str) -> None:
    """Best-effort: mark a discussion row as failed when the local pipeline blows up."""
    from argus_core.db.models import DiscussionRunModel
    from argus_core.db.session import session_scope
    from argus_core.schemas import DiscussionStatus

    try:
        async with session_scope() as session:
            row = await session.get(DiscussionRunModel, UUID(discussion_id))
            if row is not None:
                row.status = DiscussionStatus.FAILED.value
                row.error = error[:2000]
    except Exception as exc:
        logger.warning(
            "discussion.mark_failed.failed",
            discussion_id=discussion_id,
            error=str(exc),
        )


class DiscussionLauncher:
    """Fire-and-forget submission of a discussion.

    Returns the discussion_id the caller should expose to clients. The actual
    work runs out-of-band — Temporal in prod, an asyncio task locally.
    """

    async def start(self, topic: str, vertical: str, discussion_id: str) -> str:
        settings = get_settings()
        try:
            client = await _connect_with_timeout()
        except (TimeoutError, ConnectionError, OSError) as exc:
            logger.warning(
                "discussion.launcher.temporal_unavailable",
                discussion_id=discussion_id,
                error=str(exc),
            )
            _spawn_background(
                _run_activities_directly(topic, vertical, discussion_id)
            )
            return discussion_id
        except Exception as exc:
            logger.warning(
                "discussion.launcher.temporal_unavailable",
                discussion_id=discussion_id,
                error=str(exc),
            )
            _spawn_background(
                _run_activities_directly(topic, vertical, discussion_id)
            )
            return discussion_id

        await client.start_workflow(
            "DiscussionWorkflow",
            args=[topic, vertical, discussion_id],
            id=f"discussion-{discussion_id}",
            task_queue=settings.temporal_task_queue,
        )
        logger.info(
            "discussion.launcher.workflow_started",
            discussion_id=discussion_id,
            workflow_id=f"discussion-{discussion_id}",
        )
        return discussion_id


_default_launcher = DiscussionLauncher()


def get_launcher() -> DiscussionLauncher:
    """FastAPI dependency hook. Tests override this to inject a fake launcher."""
    return _default_launcher
