"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-25
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(length=512), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("wikidata_id", sa.String(length=32), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])
    op.create_index("ix_entities_wikidata_id", "entities", ["wikidata_id"])

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("feed_url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("license", sa.String(length=128), nullable=True),
        sa.Column("trust_tier", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("publisher", sa.String(length=256), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.UniqueConstraint("content_hash", name="uq_sources_content_hash"),
    )
    op.create_index("ix_sources_url", "sources", ["url"])
    op.create_index("ix_sources_content_hash", "sources", ["content_hash"], unique=True)

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="unverified"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("contradicting_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("affected_entities", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("agent_consensus", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_claims_status", "claims", ["status"])

    op.create_table(
        "relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_relations_subject_id", "relations", ["subject_id"])
    op.create_index("ix_relations_object_id", "relations", ["object_id"])
    op.create_index("ix_relations_relation_type", "relations", ["relation_type"])

    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("frame", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("knowledge_emphasis", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "discussion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("vertical", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planning"),
        sa.Column("persona_ids", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("evidence_pack", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("final_claim_ids", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_discussion_runs_vertical", "discussion_runs", ["vertical"])
    op.create_index("ix_discussion_runs_status", "discussion_runs", ["status"])

    op.create_table(
        "agent_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("discussion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discussion_runs.id"), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_messages_discussion_id", "agent_messages", ["discussion_id"])
    op.create_index("ix_agent_messages_role", "agent_messages", ["role"])


def downgrade() -> None:
    op.drop_index("ix_agent_messages_role", table_name="agent_messages")
    op.drop_index("ix_agent_messages_discussion_id", table_name="agent_messages")
    op.drop_table("agent_messages")

    op.drop_index("ix_discussion_runs_status", table_name="discussion_runs")
    op.drop_index("ix_discussion_runs_vertical", table_name="discussion_runs")
    op.drop_table("discussion_runs")

    op.drop_table("personas")

    op.drop_index("ix_relations_relation_type", table_name="relations")
    op.drop_index("ix_relations_object_id", table_name="relations")
    op.drop_index("ix_relations_subject_id", table_name="relations")
    op.drop_table("relations")

    op.drop_index("ix_claims_status", table_name="claims")
    op.drop_table("claims")

    op.drop_index("ix_sources_content_hash", table_name="sources")
    op.drop_index("ix_sources_url", table_name="sources")
    op.drop_table("sources")

    op.drop_index("ix_entities_wikidata_id", table_name="entities")
    op.drop_index("ix_entities_entity_type", table_name="entities")
    op.drop_index("ix_entities_canonical_name", table_name="entities")
    op.drop_table("entities")
