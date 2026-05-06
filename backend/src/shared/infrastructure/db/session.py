"""
Async SQLAlchemy engine and session factory.

context.md §5: SQLAlchemy (async via asyncpg).
context.md §14: DATABASE_URL must include ssl=require in production.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "See .env.example for required format."
        )
    return url


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create the async SQLAlchemy engine.

    Supabase: Uses PgBouncer transaction mode (port 6543).
              asyncpg requires statement_cache_size=0 to disable prepared statements.
              ssl=True uses asyncpg's internal verified SSL context — correctly sends
              TLS SNI header required by Supabase PgBouncer for tenant routing.
    Local dev: Direct connection, no special args needed.
    """
    url = database_url or _get_database_url()

    connect_args: dict = {}
    is_supabase = "supabase.com" in url or "supabase" in url
    if is_supabase:
        # ssl=True tells asyncpg to use ssl.create_default_context() which:
        #   1. Correctly sends TLS SNI (required by Supabase PgBouncer for tenant routing)
        #   2. Verifies the server cert against the system CA store
        # Supabase PgBouncer uses a private PKI (Supabase Root 2021 CA) — NOT any public CA.
        # The Dockerfile installs supabase-root-ca.pem into /usr/local/share/ca-certificates/
        # and runs update-ca-certificates so the system trust store includes it.
        connect_args["ssl"] = True
        connect_args["statement_cache_size"] = 0
        connect_args["server_settings"] = {"application_name": "cadencia-backend"}

    return create_async_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=os.environ.get("DEBUG", "false").lower() == "true",
        connect_args=connect_args,
    )


# Module-level engine and session factory — initialised once at startup.
# Replaced in tests via dependency injection.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,   # avoid lazy-load after commit
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency that yields a single AsyncSession per request.

    Usage in router:
        async def my_endpoint(session: AsyncSession = Depends(get_db_session)):
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
