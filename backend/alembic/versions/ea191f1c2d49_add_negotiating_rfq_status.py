"""Add NEGOTIATING to RFQ status check constraint

Revision ID: ea191f1c2d49
Revises: ea191f1c2d48
Create Date: 2026-04-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'ea191f1c2d49'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old constraint and create new one with NEGOTIATING
    op.drop_constraint('ck_rfqs_status', 'rfqs', type_='check')
    op.create_check_constraint(
        'ck_rfqs_status',
        'rfqs',
        "status IN ('DRAFT','PARSED','MATCHED','NEGOTIATING','CONFIRMED','SETTLED')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_rfqs_status', 'rfqs', type_='check')
    op.create_check_constraint(
        'ck_rfqs_status',
        'rfqs',
        "status IN ('DRAFT','PARSED','MATCHED','CONFIRMED','SETTLED')",
    )
