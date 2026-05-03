"""Add creator_address to escrow_contracts for Pera wallet deploy.

Revision ID: 009
Revises: 008
Create Date: 2026-04-12

When the escrow is deployed via Pera Wallet, the deployer's address becomes
the contract creator. This address is stored so that subsequent release/refund
operations can validate that the signer matches the creator.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escrow_contracts",
        sa.Column("creator_address", sa.String(58), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("escrow_contracts", "creator_address")
