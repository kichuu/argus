from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    """A fetched document, feed item, API record, etc.

    `raw_text` is the canonical text used for char offsets in EvidenceRef.
    The exact bytes are stored separately in object storage keyed by content_hash.
    """

    id: UUID = Field(default_factory=uuid4)
    url: HttpUrl | None = None
    feed_url: HttpUrl | None = None
    title: str
    content_hash: str = Field(description="sha256 hex digest of raw_text")
    raw_text: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    license: str | None = None
    trust_tier: int = Field(ge=1, le=4, default=4)
    publisher: str | None = None
    language: str | None = None
