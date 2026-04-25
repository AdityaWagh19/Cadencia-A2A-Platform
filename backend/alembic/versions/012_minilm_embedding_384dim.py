"""Resize embedding columns from 1536-dim (Gemini) to 384-dim (MiniLM).

Switches from Gemini API embeddings to local sentence-transformers
(all-MiniLM-L6-v2) which produces 384-dimensional vectors.
No API key needed, runs on CPU.

Drops and recreates HNSW index since dimension changed.
Existing embeddings are cleared (re-ingest via /v1/agent-memory/ingest).

Revision ID: 012
Revises: 011
Create Date: 2026-04-21
"""

from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Resize vector columns from 1536 to 384 dimensions."""

    # ── agent_memory table ───────────────────────────────────────────────────
    # Drop HNSW index (dimension is baked into the index)
    op.execute("DROP INDEX IF EXISTS agent_memory_hnsw")

    # Clear existing embeddings (dimension mismatch makes them unusable)
    op.execute("UPDATE agent_memory SET embedding = NULL")

    # Alter column type from VECTOR(1536) to VECTOR(384)
    op.execute("ALTER TABLE agent_memory ALTER COLUMN embedding TYPE VECTOR(384)")

    # Recreate HNSW index for 384-dim vectors
    op.execute("""
        CREATE INDEX IF NOT EXISTS agent_memory_hnsw
        ON agent_memory USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Update column comment
    op.execute("""
        COMMENT ON COLUMN agent_memory.embedding IS
        '384-dimensional vector from MiniLM (all-MiniLM-L6-v2). '
        'Indexed with HNSW for sub-50ms cosine similarity search.'
    """)

    # ── agent_profiles table ─────────────────────────────────────────────────
    # Clear existing history embeddings
    op.execute("UPDATE agent_profiles SET history_embedding = NULL")

    # Alter column type
    op.execute(
        "ALTER TABLE agent_profiles ALTER COLUMN history_embedding TYPE VECTOR(384)"
    )


def downgrade() -> None:
    """Revert vector columns from 384 back to 1536 dimensions."""

    # ── agent_memory ─────────────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS agent_memory_hnsw")
    op.execute("UPDATE agent_memory SET embedding = NULL")
    op.execute("ALTER TABLE agent_memory ALTER COLUMN embedding TYPE VECTOR(1536)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS agent_memory_hnsw
        ON agent_memory USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ── agent_profiles ───────────────────────────────────────────────────────
    op.execute("UPDATE agent_profiles SET history_embedding = NULL")
    op.execute(
        "ALTER TABLE agent_profiles ALTER COLUMN history_embedding TYPE VECTOR(1536)"
    )
