"""Add PENDING_APPROVAL/REJECTED escrow states and approval audit columns.

Revision ID: 011
Revises: 010
Create Date: 2026-04-13

Changes:
  1. Drop old CHECK constraint on escrow_contracts.status
  2. Create new CHECK constraint allowing PENDING_APPROVAL, DEPLOYED, FUNDED,
     RELEASED, REFUNDED, REJECTED
  3. Change default for status from 'DEPLOYED' to 'PENDING_APPROVAL'
  4. Make buyer_algorand_address and seller_algorand_address nullable
     (they're set at approval time, not at escrow creation)
  5. Add approved_by (UUID), approved_at (timestamptz) for audit trail
  6. Add agreed_price_inr (float), buyer_enterprise_id (UUID),
     seller_enterprise_id (UUID) for admin dashboard display
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old CHECK constraint and create new one with expanded statuses
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ('PENDING_APPROVAL','DEPLOYED','FUNDED','RELEASED','REFUNDED','REJECTED'))"
    )

    # 2. Change status default from DEPLOYED to PENDING_APPROVAL
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN status SET DEFAULT 'PENDING_APPROVAL'"
    )

    # 3. Make buyer/seller addresses nullable (populated at approval time)
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN buyer_algorand_address DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN seller_algorand_address DROP NOT NULL"
    )

    # 4. Add approval audit columns
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD COLUMN IF NOT EXISTS approved_by UUID"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ"
    )

    # 5. Add agreed price and enterprise IDs for admin display
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD COLUMN IF NOT EXISTS agreed_price_inr DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD COLUMN IF NOT EXISTS buyer_enterprise_id UUID"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD COLUMN IF NOT EXISTS seller_enterprise_id UUID"
    )


def downgrade() -> None:
    # Remove new columns
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP COLUMN IF EXISTS seller_enterprise_id"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP COLUMN IF EXISTS buyer_enterprise_id"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP COLUMN IF EXISTS agreed_price_inr"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP COLUMN IF EXISTS approved_at"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP COLUMN IF EXISTS approved_by"
    )

    # Restore NOT NULL on addresses
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN seller_algorand_address SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN buyer_algorand_address SET NOT NULL"
    )

    # Restore old default and CHECK constraint
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ALTER COLUMN status SET DEFAULT 'DEPLOYED'"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ('DEPLOYED','FUNDED','RELEASED','REFUNDED'))"
    )
