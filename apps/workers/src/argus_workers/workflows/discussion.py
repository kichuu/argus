from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class DiscussionWorkflow:
    @workflow.run
    async def run(
        self,
        topic: str,
        vertical: str,
        discussion_id: str | None = None,
    ) -> dict[str, Any]:
        retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=2),
            maximum_attempts=3,
        )

        did: str = await workflow.execute_activity(
            "start_discussion",
            args=[topic, vertical, discussion_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry,
        )

        await workflow.execute_activity(
            "assemble_evidence_pack",
            did,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry,
        )

        graph_result: dict[str, Any] = await workflow.execute_activity(
            "run_discussion_graph",
            did,
            start_to_close_timeout=timedelta(minutes=20),
            retry_policy=retry,
        )

        await workflow.execute_activity(
            "persist_results",
            args=[did, graph_result],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )

        return {"discussion_id": did, **graph_result}
