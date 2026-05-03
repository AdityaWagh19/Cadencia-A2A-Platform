"""Clean up stale escrow rows from the old shared-app model

Revision ID: ea191f1c2d52
Revises: ea191f1c2d51
Create Date: 2026-05-01 00:00:00.000000

The previous shared-app model stored the same algo_app_id in every escrow row,
which violated the uq_escrow_contracts_algo_app_id unique constraint on every
deal after the first.

Now each escrow deploys its own contract, so the unique constraint is correct.
This migration resets any escrow rows that were recorded under the old shared
app_id but have not yet moved real funds (PENDING_APPROVAL / APPROVED / DEPLOYED).
Resetting them allows sellers to accept their deal again, which will deploy a
fresh per-escrow contract.

Rows that are FUNDED, DISPATCHED, RELEASED, or REFUNDED are left untouched.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'ea191f1c2d52'
down_revision: Union[str, None] = 'ea191f1c2d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reset on-chain references for pre-funded rows so the unique constraint
    # doesn't block the next deploy. Return them to PENDING_APPROVAL so sellers
    # can accept again and a fresh per-escrow contract will be deployed.
    op.execute("""
        UPDATE escrow_contracts
        SET    algo_app_id      = NULL,
               deploy_tx_id     = NULL,
               status           = 'PENDING_APPROVAL',
               updated_at       = now()
        WHERE  status IN ('PENDING_APPROVAL', 'APPROVED', 'DEPLOYED')
          AND  algo_app_id IS NOT NULL
    """)


def downgrade() -> None:
    # No meaningful rollback — the old shared app_id values cannot be recovered.
    pass
