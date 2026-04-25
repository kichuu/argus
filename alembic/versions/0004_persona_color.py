"""persona color

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-25

Adds an optional `color` column to the personas table so the frontend can
render persona avatars consistently across discussions. Nullable with no
backfill -- the agent layer derives a stable fallback color from the frame
hash when `color` is null.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column("color", sa.String(length=24), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("personas", "color")
