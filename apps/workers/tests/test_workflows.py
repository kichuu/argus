from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_ingestion_workflow_calls_activities_in_order() -> None:
    from argus_workers.workflows.ingestion import IngestionWorkflow

    fake = AsyncMock()
    # fetch_source returns one source id; extract_claims returns one claim id;
    # verify_claims and index_evidence return whatever.
    fake.side_effect = [
        ["src-1"],
        ["claim-1"],
        {"verified": 1},
        {"indexed": 0},
    ]

    with patch("temporalio.workflow.execute_activity", new=fake):
        wf = IngestionWorkflow()
        result = await wf.run([{"kind": "rss", "feed_urls": ["http://example.com/feed"]}])

    assert result["claim_ids"] == ["claim-1"]
    names = [call.args[0] for call in fake.call_args_list]
    assert names == [
        "fetch_source",
        "extract_claims",
        "verify_claims",
        "index_evidence",
    ]


@pytest.mark.asyncio
async def test_ingestion_workflow_retry_policies() -> None:
    from argus_workers.workflows.ingestion import IngestionWorkflow

    fake = AsyncMock()
    fake.side_effect = [["src-1"], ["claim-1"], {"verified": 1}, {"indexed": 0}]

    with patch("temporalio.workflow.execute_activity", new=fake):
        wf = IngestionWorkflow()
        await wf.run([{"kind": "rss", "feed_urls": ["http://example.com/feed"]}])

    fetch_call = fake.call_args_list[0]
    extract_call = fake.call_args_list[1]
    verify_call = fake.call_args_list[2]

    assert fetch_call.kwargs["retry_policy"].maximum_attempts == 3
    assert extract_call.kwargs["retry_policy"].maximum_attempts == 1
    assert verify_call.kwargs["retry_policy"].maximum_attempts == 1
    assert fetch_call.kwargs["start_to_close_timeout"] == timedelta(seconds=60)
    assert extract_call.kwargs["start_to_close_timeout"] == timedelta(seconds=120)


@pytest.mark.asyncio
async def test_discussion_workflow_calls_activities_in_order() -> None:
    from argus_workers.workflows.discussion import DiscussionWorkflow

    fake = AsyncMock()
    fake.side_effect = [
        "did-1",  # start_discussion
        {"discussion_id": "did-1", "evidence_count": 5},  # assemble_evidence_pack
        {"messages": [], "final_claims": []},  # run_discussion_graph
        {"persisted": True},  # persist_results
    ]

    with patch("temporalio.workflow.execute_activity", new=fake):
        wf = DiscussionWorkflow()
        result = await wf.run("test topic", "geopolitics")

    assert result["discussion_id"] == "did-1"
    names = [call.args[0] for call in fake.call_args_list]
    assert names == [
        "start_discussion",
        "assemble_evidence_pack",
        "run_discussion_graph",
        "persist_results",
    ]
    graph_call = fake.call_args_list[2]
    assert graph_call.kwargs["retry_policy"].maximum_attempts == 1
    assert graph_call.kwargs["start_to_close_timeout"] == timedelta(seconds=300)
