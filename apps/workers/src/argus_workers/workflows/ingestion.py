from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class IngestionWorkflow:
    """fetch -> extract -> verify -> index.

    Fetch is retried (transient HTTP); LLM-driven activities run with
    maximum_attempts=1 because rerunning a partially-charged extraction is
    worse than failing the workflow loud.
    """

    @workflow.run
    async def run(self, source_configs: list[dict[str, Any]]) -> dict[str, Any]:
        fetch_retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=2),
            maximum_attempts=3,
        )
        once = RetryPolicy(maximum_attempts=1)

        all_claim_ids: list[str] = []
        per_source: list[dict[str, Any]] = []

        for cfg in source_configs:
            source_ids: list[str] = await workflow.execute_activity(
                "fetch_source",
                cfg,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=fetch_retry,
            )

            for sid in source_ids:
                claim_ids: list[str] = await workflow.execute_activity(
                    "extract_claims",
                    sid,
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=once,
                )
                if claim_ids:
                    await workflow.execute_activity(
                        "verify_claims",
                        claim_ids,
                        start_to_close_timeout=timedelta(seconds=120),
                        retry_policy=once,
                    )
                    await workflow.execute_activity(
                        "index_evidence",
                        sid,
                        start_to_close_timeout=timedelta(seconds=60),
                        retry_policy=once,
                    )
                    all_claim_ids.extend(claim_ids)
                per_source.append({"source_id": sid, "claim_ids": claim_ids})

        return {"claim_ids": all_claim_ids, "per_source": per_source}
