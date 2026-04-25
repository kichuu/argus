"""persona designer extensions

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25

Adds the PersonaDesigner UI fields (temperature, redlines, bias,
model_assignment) plus an updated_at audit column to the personas table.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
    )
    op.add_column(
        "personas",
        sa.Column(
            "redlines",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "personas",
        sa.Column("bias", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "personas",
        sa.Column("model_assignment", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "personas",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("personas", "updated_at")
    op.drop_column("personas", "model_assignment")
    op.drop_column("personas", "bias")
    op.drop_column("personas", "redlines")
    op.drop_column("personas", "temperature")
