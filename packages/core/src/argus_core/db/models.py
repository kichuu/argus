"""SQLAlchemy 2.0 ORM models that mirror the Pydantic schemas.

Pydantic schemas are the I/O contract; these models are the persistence layer.
JSONB columns hold nested evidence/relation arrays where graph traversal is
not needed; AGE handles entity-relation traversal separately.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argus_core.db.base import Base


def _utc_now() -> datetime:

    return datetime.now(UTC)


class EntityModel(Base):
    __tablename__ = "entities"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(512), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    wikidata_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    feed_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str] = mapped_column(String(1024))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trust_tier: Mapped[int] = mapped_column(Integer, default=4)
    publisher: Mapped[str | None] = mapped_column(String(256), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)


class ClaimModel(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="unverified", index=True)
    confidence: Mapped[float] = mapped_column(Float)
    supporting_evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    contradicting_evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    affected_entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    agent_consensus: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )


class RelationModel(Base):
    __tablename__ = "relations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), index=True
    )
    evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class PersonaModel(Base):
    __tablename__ = "personas"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    frame: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    knowledge_emphasis: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class DiscussionRunModel(Base):
    __tablename__ = "discussion_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(Text)
    vertical: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="planning", index=True)
    persona_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    evidence_pack: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    final_claim_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    messages: Mapped[list["AgentMessageModel"]] = relationship(
        back_populates="discussion", cascade="all, delete-orphan"
    )


class AgentMessageModel(Base):
    __tablename__ = "agent_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("discussion_runs.id"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String(128))
    persona_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    parent_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )

    discussion: Mapped[DiscussionRunModel] = relationship(back_populates="messages")
