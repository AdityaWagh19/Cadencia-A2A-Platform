"""Add missing columns to negotiation_sessions.

Revision ID: 010
Revises: 009
Create Date: 2026-04-12

The ORM model has schema_failure_count and stall_counter columns that were
never created in any migration, causing UndefinedColumnError on session queries.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "ADD COLUMN IF NOT EXISTS schema_failure_count INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "ADD COLUMN IF NOT EXISTS stall_counter INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.drop_column("negotiation_sessions", "stall_counter")
    op.drop_column("negotiation_sessions", "schema_failure_count")
