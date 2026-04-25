"""Enhanced onboarding: addresses, catalogue, capacity, delivery feasibility.

New tables:
  - addresses: Reusable address entity (facility, delivery, office)
  - catalogue_items: Seller product catalogue with bulk pricing tiers
  - seller_capacity_profiles: Production capacity and logistics data
  - pincode_geocodes: Indian pincode geocoding lookup (~19K rows)

Altered tables:
  - enterprises: facility_type, payment_terms, certifications, business fields
  - rfqs: delivery_pincode, delivery_city, delivery_state, lead_time, payment
  - matches: scoring breakdown (semantic, delivery, capacity, price, proximity, composite)

Revision ID: 013
Revises: 012
Create Date: 2026-04-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # ── New table: addresses ─────────────────────────────────────────────────
    op.create_table(
        "addresses",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("enterprise_id", UUID(as_uuid=True), sa.ForeignKey("enterprises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address_type", sa.String(30), nullable=False),
        sa.Column("address_line1", sa.String(500), nullable=False),
        sa.Column("address_line2", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("pincode", sa.String(6), nullable=False),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("is_primary", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "address_type IN ('FACILITY','DELIVERY','REGISTERED_OFFICE','WAREHOUSE')",
            name="ck_addresses_address_type",
        ),
    )
    op.create_index("ix_addresses_enterprise_id", "addresses", ["enterprise_id"])
    op.create_index("ix_addresses_pincode", "addresses", ["pincode"])

    # ── New table: catalogue_items ───────────────────────────────────────────
    op.create_table(
        "catalogue_items",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("enterprise_id", UUID(as_uuid=True), sa.ForeignKey("enterprises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("hsn_code", sa.String(8), nullable=False),
        sa.Column("product_category", sa.String(50), nullable=False),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("specification_text", sa.Text, nullable=True),
        sa.Column("unit", sa.String(20), server_default="MT", nullable=False),
        sa.Column("price_per_unit_inr", sa.Numeric(18, 4), nullable=False),
        sa.Column("bulk_pricing_tiers", JSONB, nullable=True),
        sa.Column("moq", sa.Numeric(12, 4), nullable=False),
        sa.Column("max_order_qty", sa.Numeric(12, 4), nullable=False),
        sa.Column("lead_time_days", sa.Integer, nullable=False),
        sa.Column("in_stock_qty", sa.Numeric(12, 4), server_default="0", nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("certifications", ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("moq > 0", name="ck_catalogue_moq_positive"),
        sa.CheckConstraint("max_order_qty >= moq", name="ck_catalogue_max_gte_moq"),
        sa.CheckConstraint("price_per_unit_inr > 0", name="ck_catalogue_price_positive"),
        sa.CheckConstraint("lead_time_days BETWEEN 1 AND 180", name="ck_catalogue_lead_time"),
        sa.CheckConstraint(
            "product_category IN ('HR_COIL','CR_COIL','TMT_BAR','WIRE_ROD','BILLET','SLAB','PLATE','PIPE','SHEET','ANGLE','CHANNEL','BEAM','CUSTOM')",
            name="ck_catalogue_product_category",
        ),
    )
    op.create_index("ix_catalogue_items_enterprise_id", "catalogue_items", ["enterprise_id"])
    op.create_index("ix_catalogue_items_category", "catalogue_items", ["product_category"])
    op.create_index(
        "ix_catalogue_items_active",
        "catalogue_items",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # ── New table: seller_capacity_profiles ───────────────────────────────────
    op.create_table(
        "seller_capacity_profiles",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("enterprise_id", UUID(as_uuid=True), sa.ForeignKey("enterprises.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("monthly_production_capacity_mt", sa.Numeric(12, 4), nullable=False),
        sa.Column("current_utilization_pct", sa.Integer, server_default="0", nullable=True),
        sa.Column("available_capacity_mt", sa.Numeric(12, 4), nullable=True),
        sa.Column("num_production_lines", sa.Integer, server_default="1", nullable=True),
        sa.Column("shift_pattern", sa.String(30), server_default="SINGLE_SHIFT", nullable=False),
        sa.Column("avg_dispatch_days", sa.Integer, server_default="3", nullable=False),
        sa.Column("max_delivery_radius_km", sa.Integer, nullable=True),
        sa.Column("has_own_transport", sa.Boolean, server_default="false", nullable=False),
        sa.Column("preferred_transport_modes", ARRAY(sa.String), nullable=True),
        sa.Column("ex_works_available", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("monthly_production_capacity_mt > 0", name="ck_capacity_positive"),
        sa.CheckConstraint("current_utilization_pct BETWEEN 0 AND 100", name="ck_utilization_range"),
        sa.CheckConstraint(
            "shift_pattern IN ('SINGLE_SHIFT','DOUBLE_SHIFT','TRIPLE_SHIFT','CONTINUOUS')",
            name="ck_shift_pattern",
        ),
    )

    # ── New table: pincode_geocodes ──────────────────────────────────────────
    op.create_table(
        "pincode_geocodes",
        sa.Column("pincode", sa.String(6), primary_key=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("region", sa.String(20), nullable=True),
    )
    op.create_index("ix_pincode_geocodes_state", "pincode_geocodes", ["state"])

    # ── Alter table: enterprises ─────────────────────────────────────────────
    op.add_column("enterprises", sa.Column("facility_type", sa.String(30), nullable=True))
    op.add_column("enterprises", sa.Column("payment_terms_accepted", ARRAY(sa.String), nullable=True))
    op.add_column("enterprises", sa.Column("credit_period_days", sa.Integer, nullable=True))
    op.add_column("enterprises", sa.Column("years_in_operation", sa.Integer, nullable=True))
    op.add_column("enterprises", sa.Column("annual_turnover_inr", sa.Numeric(18, 2), nullable=True))
    op.add_column("enterprises", sa.Column("quality_certifications", ARRAY(sa.String), nullable=True))
    op.add_column("enterprises", sa.Column("test_certificate_available", sa.Boolean, server_default="false", nullable=True))
    op.add_column("enterprises", sa.Column("third_party_inspection_allowed", sa.Boolean, server_default="false", nullable=True))

    # ── Alter table: rfqs ────────────────────────────────────────────────────
    op.add_column("rfqs", sa.Column("delivery_pincode", sa.String(6), nullable=True))
    op.add_column("rfqs", sa.Column("delivery_city", sa.String(100), nullable=True))
    op.add_column("rfqs", sa.Column("delivery_state", sa.String(50), nullable=True))
    op.add_column("rfqs", sa.Column("max_acceptable_lead_time_days", sa.Integer, nullable=True))
    op.add_column("rfqs", sa.Column("requires_test_certificate", sa.Boolean, server_default="false", nullable=True))
    op.add_column("rfqs", sa.Column("preferred_payment_terms", ARRAY(sa.String), nullable=True))

    # ── Alter table: matches ─────────────────────────────────────────────────
    op.add_column("matches", sa.Column("semantic_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("delivery_feasibility_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("capacity_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("price_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("proximity_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("composite_score", sa.Float, nullable=True))
    op.add_column("matches", sa.Column("estimated_delivery_days", sa.Integer, nullable=True))
    op.add_column("matches", sa.Column("distance_km", sa.Integer, nullable=True))


def downgrade() -> None:
    # ── Revert matches ───────────────────────────────────────────────────────
    op.drop_column("matches", "distance_km")
    op.drop_column("matches", "estimated_delivery_days")
    op.drop_column("matches", "composite_score")
    op.drop_column("matches", "proximity_score")
    op.drop_column("matches", "price_score")
    op.drop_column("matches", "capacity_score")
    op.drop_column("matches", "delivery_feasibility_score")
    op.drop_column("matches", "semantic_score")

    # ── Revert rfqs ──────────────────────────────────────────────────────────
    op.drop_column("rfqs", "preferred_payment_terms")
    op.drop_column("rfqs", "requires_test_certificate")
    op.drop_column("rfqs", "max_acceptable_lead_time_days")
    op.drop_column("rfqs", "delivery_state")
    op.drop_column("rfqs", "delivery_city")
    op.drop_column("rfqs", "delivery_pincode")

    # ── Revert enterprises ───────────────────────────────────────────────────
    op.drop_column("enterprises", "third_party_inspection_allowed")
    op.drop_column("enterprises", "test_certificate_available")
    op.drop_column("enterprises", "quality_certifications")
    op.drop_column("enterprises", "annual_turnover_inr")
    op.drop_column("enterprises", "years_in_operation")
    op.drop_column("enterprises", "credit_period_days")
    op.drop_column("enterprises", "payment_terms_accepted")
    op.drop_column("enterprises", "facility_type")

    # ── Drop new tables ──────────────────────────────────────────────────────
    op.drop_table("pincode_geocodes")
    op.drop_table("seller_capacity_profiles")
    op.drop_table("catalogue_items")
    op.drop_table("addresses")
