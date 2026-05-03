"""Fix constraints and create missing tables.

Revision ID: 008
Revises: 007_admin_separation
Create Date: 2026-04-12

Changes:
  1. Update ck_users_role to include MEMBER (registration was failing
     because the service forces UserRole.MEMBER but the DB constraint
     only allowed enterprise-level roles).
  2. Update ck_negotiation_sessions_status to include all statuses used
     by the ORM model (INIT, BUYER_ANCHOR, SELLER_RESPONSE, ROUND_LOOP,
     WALK_AWAY, STALLED, TIMEOUT, POLICY_BREACH).
  3. Create liquidity_pools table (treasury bounded context).
  4. Create fx_positions table (treasury bounded context).
  5. Create opponent_profiles table (negotiation bounded context).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

TIMESTAMPTZ = sa.TIMESTAMP(timezone=True)

revision: str = "008"
down_revision: Union[str, None] = "007_admin_separation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Fix ck_users_role — add MEMBER ────────────────────────────────────
    # Drop both possible names: SQLAlchemy naming convention may double-prefix
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_ck_users_role")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role "
        "CHECK (role IN ("
        "'ADMIN','MEMBER','BUYER','SELLER',"
        "'COMPLIANCE_OFFICER','TREASURY_MANAGER','AUDITOR'"
        "))"
    )

    # ── 2. Fix ck_negotiation_sessions_status — add missing statuses ─────────
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "DROP CONSTRAINT IF EXISTS ck_negotiation_sessions_ck_negotiation_sessions_status"
    )
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "DROP CONSTRAINT IF EXISTS ck_negotiation_sessions_status"
    )
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "ADD CONSTRAINT ck_negotiation_sessions_status "
        "CHECK (status IN ("
        "'ACTIVE','AGREED','FAILED','EXPIRED','HUMAN_REVIEW',"
        "'INIT','BUYER_ANCHOR','SELLER_RESPONSE','ROUND_LOOP',"
        "'WALK_AWAY','STALLED','TIMEOUT','POLICY_BREACH'"
        "))"
    )

    # ── 2b. Fix ck_escrow_contracts_status — add FROZEN, drop doubled name ──
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "DROP CONSTRAINT IF EXISTS ck_escrow_contracts_status"
    )
    op.execute(
        "ALTER TABLE escrow_contracts "
        "ADD CONSTRAINT ck_escrow_contracts_status "
        "CHECK (status IN ('DEPLOYED','FUNDED','RELEASED','REFUNDED','FROZEN'))"
    )

    # ── 3. Create liquidity_pools table ──────────────────────────────────────
    op.create_table(
        "liquidity_pools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("enterprise_id", UUID(as_uuid=True),
                  sa.ForeignKey("enterprises.id"), nullable=False, unique=True),
        sa.Column("inr_balance", sa.Numeric(18, 2), nullable=False,
                  server_default="0"),
        sa.Column("usdc_balance", sa.Numeric(18, 6), nullable=False,
                  server_default="0"),
        sa.Column("algo_balance_microalgo", sa.BigInteger, nullable=False,
                  server_default="0"),
        sa.Column("last_fx_rate_inr_usd", sa.Numeric(18, 8), nullable=False,
                  server_default="0"),
        sa.Column("last_rate_updated_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("inr_balance >= 0",
                           name="ck_liquidity_pools_inr_non_negative"),
        sa.CheckConstraint("usdc_balance >= 0",
                           name="ck_liquidity_pools_usdc_non_negative"),
        sa.CheckConstraint("algo_balance_microalgo >= 0",
                           name="ck_liquidity_pools_algo_non_negative"),
    )
    op.create_index(
        "ix_liquidity_pools_enterprise_id", "liquidity_pools",
        ["enterprise_id"], unique=True,
    )

    # ── 4. Create fx_positions table ─────────────────────────────────────────
    op.create_table(
        "fx_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("enterprise_id", UUID(as_uuid=True),
                  sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("currency_pair", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(5), nullable=False),
        sa.Column("notional_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("entry_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("current_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("status", sa.String(10), nullable=False,
                  server_default="OPEN"),
        sa.Column("closed_at", TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("direction IN ('LONG', 'SHORT')",
                           name="ck_fx_positions_direction"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')",
                           name="ck_fx_positions_status"),
    )
    op.create_index("ix_fx_positions_enterprise_id", "fx_positions",
                    ["enterprise_id"])
    op.create_index("ix_fx_positions_status", "fx_positions", ["status"])

    # ── 5. Create opponent_profiles table ────────────────────────────────────
    op.create_table(
        "opponent_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("observer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("flexibility", sa.Float, nullable=False,
                  server_default="0.5"),
        sa.Column("belief", JSONB, nullable=True),
        sa.Column("rounds_observed", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_opponent_profiles_observer_target", "opponent_profiles",
        ["observer_id", "target_id"], unique=True,
    )
    op.create_index(
        "ix_opponent_profiles_target_id", "opponent_profiles", ["target_id"],
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_index("ix_opponent_profiles_target_id", "opponent_profiles")
    op.drop_index("ix_opponent_profiles_observer_target", "opponent_profiles")
    op.drop_table("opponent_profiles")

    op.drop_index("ix_fx_positions_status", "fx_positions")
    op.drop_index("ix_fx_positions_enterprise_id", "fx_positions")
    op.drop_table("fx_positions")

    op.drop_index("ix_liquidity_pools_enterprise_id", "liquidity_pools")
    op.drop_table("liquidity_pools")

    # Restore original negotiation_sessions status constraint
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "DROP CONSTRAINT IF EXISTS ck_negotiation_sessions_status"
    )
    op.execute(
        "ALTER TABLE negotiation_sessions "
        "ADD CONSTRAINT ck_negotiation_sessions_status "
        "CHECK (status IN ('ACTIVE','AGREED','FAILED','EXPIRED','HUMAN_REVIEW'))"
    )

    # Restore original users role constraint (without MEMBER)
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role "
        "CHECK (role IN ("
        "'ADMIN','BUYER','SELLER',"
        "'COMPLIANCE_OFFICER','TREASURY_MANAGER','AUDITOR'"
        "))"
    )
