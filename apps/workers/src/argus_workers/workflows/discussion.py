from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class DiscussionWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        discussion_id: str = await workflow.execute_activity(
            "start_discussion",
            payload,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        try:
            await workflow.execute_activity(
                "assemble_evidence_pack",
                discussion_id,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
            graph_result: dict[str, Any] = await workflow.execute_activity(
                "run_discussion_graph",
                discussion_id,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            persist_payload: dict[str, Any] = {
                "discussion_id": discussion_id,
                "final_claims": graph_result.get("final_claims", []),
            }
            result: dict[str, Any] = await workflow.execute_activity(
                "persist_results",
                persist_payload,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
        except Exception as exc:
            await workflow.execute_activity(
                "_mark_failed",
                {"id": discussion_id, "error": str(exc)},
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
            raise
        return {
            "discussion_id": discussion_id,
            "n_messages": graph_result.get("n_messages", 0),
            "n_claims": graph_result.get("n_claims", 0),
            "n_claims_persisted": result.get("n_claims_persisted", 0),
        }
