from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class DiscussionWorkflow:
    """start -> assemble -> run graph -> persist.

    LLM-driven activities run with maximum_attempts=1; the graph is the most
    expensive step (300s) because it spans research + personas + critic +
    synthesizer.
    """

    @workflow.run
    async def run(
        self,
        topic: str,
        vertical: str,
        discussion_id: str | None = None,
    ) -> dict[str, Any]:
        once = RetryPolicy(maximum_attempts=1)
        light_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        did: str = await workflow.execute_activity(
            "start_discussion",
            args=[topic, vertical, discussion_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=light_retry,
        )

        await workflow.execute_activity(
            "assemble_evidence_pack",
            did,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=light_retry,
        )

        graph_result: dict[str, Any] = await workflow.execute_activity(
            "run_discussion_graph",
            did,
            start_to_close_timeout=timedelta(seconds=300),
            retry_policy=once,
        )

        await workflow.execute_activity(
            "persist_results",
            args=[did, graph_result],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=light_retry,
        )

        return {"discussion_id": did, **graph_result}
