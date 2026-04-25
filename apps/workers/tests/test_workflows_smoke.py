def test_workflow_imports() -> None:
    from argus_workers.workflows.discussion import DiscussionWorkflow
    from argus_workers.workflows.ingestion import IngestionWorkflow

    assert DiscussionWorkflow is not None
    assert IngestionWorkflow is not None


def test_activity_imports() -> None:
    from argus_workers.activities.discussion import (
        assemble_evidence_pack,
        persist_results,
        run_discussion_graph,
        start_discussion,
    )
    from argus_workers.activities.extract import extract_claims
    from argus_workers.activities.fetch import fetch_source, index_evidence
    from argus_workers.activities.verify import verify_claims

    for fn in (
        fetch_source,
        index_evidence,
        extract_claims,
        verify_claims,
        start_discussion,
        assemble_evidence_pack,
        run_discussion_graph,
        persist_results,
    ):
        assert callable(fn)
