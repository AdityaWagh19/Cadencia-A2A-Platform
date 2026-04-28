"""Add DISPATCHED to escrow_contracts status constraint and seed general playbook

Revision ID: ea191f1c2d51
Revises: ea191f1c2d50
Create Date: 2026-04-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'ea191f1c2d51'
down_revision: Union[str, None] = 'ea191f1c2d50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add DISPATCHED to escrow status constraint (ESC-02)
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ("
        "'PENDING_APPROVAL','APPROVED','DEPLOYED','FUNDED','DISPATCHED',"
        "'RELEASED','REFUNDED','REJECTED','FROZEN'"
        "))"
    )

    # 2. Patch stuck escrows with NULL tx_ids (ESC-02 data fix)
    op.execute(
        "UPDATE escrow_contracts "
        "SET fund_tx_id = COALESCE(fund_tx_id, 'platform-funded'), "
        "    deploy_tx_id = COALESCE(deploy_tx_id, 'platform-deployed') "
        "WHERE algo_app_id IS NOT NULL "
        "  AND (fund_tx_id IS NULL OR deploy_tx_id IS NULL)"
    )

    # 3. Seed a general-purpose industry playbook (NEG-05)
    op.execute(
        """
        INSERT INTO industry_playbooks (hsn_prefix, industry_name, playbook_text, strategy_hints, is_active)
        SELECT '00', 'general',
        'General B2B trade negotiation playbook for all commodity verticals.',
        '{"pricing_norms": "Negotiate total order value. Opening: buyer 15-20%% below budget, seller 15-20%% above cost. Converge in 8-12 rounds.","payment_schedules": ["Advance", "LC at sight", "LC 30/60/90 days", "NET 30", "NET 60"],"typical_discount_ranges": "2-8%% from opening for bulk orders. Loyalty discounts 1-3%%.","seasonal_factors": "Year-end/quarter-end: buyers have higher urgency. Festival seasons: supply tightens.","standard_slas": "Delivery: 7-45 days. Quality inspection: 3-5 days. Payment release: within 2 days of delivery.","buyer_tactics": "Start with lower anchor, emphasise volume and repeat business, use payment terms as leverage.","seller_tactics": "Anchor high, justify on quality and reliability, offer flexibility on payment terms not price."}'::jsonb,
        true
        WHERE NOT EXISTS (
            SELECT 1 FROM industry_playbooks WHERE industry_name = 'general' AND is_active = true
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ("
        "'PENDING_APPROVAL','APPROVED','DEPLOYED','FUNDED',"
        "'RELEASED','REFUNDED','REJECTED','FROZEN'"
        "))"
    )
    op.execute(
        "DELETE FROM industry_playbooks WHERE industry_name = 'general' AND hsn_prefix = '00'"
    )
