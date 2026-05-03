"""Admin separation and RLS policies

Revision ID: 007_admin_separation
Revises: ea191f1c2d48
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "007_admin_separation"
down_revision = "ea191f1c2d48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create admin_private schema ────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS admin_private")

    # ── 2. Create admin_users table (separate from public.users) ─────────────
    op.create_table(
        "admin_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="admin_private",
    )

    op.create_index(
        "ix_admin_users_email",
        "admin_users",
        ["email"],
        unique=True,
        schema="admin_private",
    )

    # ── 3. Add profiles table with role CHECK constraint ─────────────────────
    # This serves as the Supabase-compatible profiles table with role enforcement
    op.create_table(
        "profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enterprise_id", UUID(as_uuid=True), sa.ForeignKey("enterprises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('buyer', 'seller')", name="ck_profiles_role"),
    )

    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)
    op.create_index("ix_profiles_enterprise_id", "profiles", ["enterprise_id"])

    # ── 4. Enable RLS on key tables ──────────────────────────────────────────
    for table in ("enterprises", "users", "rfqs", "profiles"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # ── 5. RLS Policies — enterprises ─────────────────────────────────────────
    # Users can only see their own enterprise
    op.execute("""
        CREATE POLICY enterprises_own_enterprise ON enterprises
        FOR SELECT
        USING (
            id IN (
                SELECT enterprise_id FROM users
                WHERE id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    # ── 6. RLS Policies — users ───────────────────────────────────────────────
    # Users can only see themselves
    op.execute("""
        CREATE POLICY users_own_row ON users
        FOR SELECT
        USING (
            id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    # Users can only update themselves
    op.execute("""
        CREATE POLICY users_update_own ON users
        FOR UPDATE
        USING (
            id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    # ── 7. RLS Policies — rfqs ────────────────────────────────────────────────
    # Buyers can see RFQs they created
    op.execute("""
        CREATE POLICY rfqs_buyer_own ON rfqs
        FOR SELECT
        USING (
            enterprise_id IN (
                SELECT enterprise_id FROM users
                WHERE id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    # ── 8. RLS Policies — profiles ────────────────────────────────────────────
    op.execute("""
        CREATE POLICY profiles_own_row ON profiles
        FOR SELECT
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    op.execute("""
        CREATE POLICY profiles_update_own ON profiles
        FOR UPDATE
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    # ── 9. Grant admin_private schema access only to service role ─────────────
    # The application uses superuser/service-role to access admin_private
    # Normal user connections should not have access
    op.execute("REVOKE ALL ON SCHEMA admin_private FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA admin_private FROM PUBLIC")

    # Supabase: service_role must have explicit schema access
    # (REVOKE FROM PUBLIC blocks all non-superuser roles including service_role)
    # Wrapped in DO block — role only exists on Supabase, not local Docker Postgres
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                EXECUTE 'GRANT USAGE ON SCHEMA admin_private TO service_role';
                EXECUTE 'GRANT ALL ON ALL TABLES IN SCHEMA admin_private TO service_role';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA admin_private GRANT ALL ON TABLES TO service_role';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop RLS policies
    for policy, table in [
        ("profiles_update_own", "profiles"),
        ("profiles_own_row", "profiles"),
        ("rfqs_buyer_own", "rfqs"),
        ("users_update_own", "users"),
        ("users_own_row", "users"),
        ("enterprises_own_enterprise", "enterprises"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")

    # Disable RLS
    for table in ("profiles", "rfqs", "users", "enterprises"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop profiles table
    op.drop_index("ix_profiles_enterprise_id", table_name="profiles")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")

    # Drop admin_users table
    op.drop_index("ix_admin_users_email", table_name="admin_users", schema="admin_private")
    op.drop_table("admin_users", schema="admin_private")

    # Revoke service_role grants before dropping schema (Supabase-only)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA admin_private FROM service_role';
                EXECUTE 'REVOKE USAGE ON SCHEMA admin_private FROM service_role';
            END IF;
        END $$;
    """)

    # Drop admin_private schema
    op.execute("DROP SCHEMA IF EXISTS admin_private CASCADE")
