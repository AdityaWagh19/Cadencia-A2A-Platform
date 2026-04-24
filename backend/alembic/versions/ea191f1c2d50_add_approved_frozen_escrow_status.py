"""Add APPROVED and FROZEN to escrow_contracts status check constraint

Revision ID: ea191f1c2d50
Revises: ea191f1c2d49
Create Date: 2026-04-25 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'ea191f1c2d50'
down_revision: Union[str, None] = 'ea191f1c2d49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ('PENDING_APPROVAL','APPROVED','DEPLOYED','FUNDED','RELEASED','REFUNDED','REJECTED','FROZEN'))"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ('PENDING_APPROVAL','DEPLOYED','FUNDED','RELEASED','REFUNDED','REJECTED'))"
    )
