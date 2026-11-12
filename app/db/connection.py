"""Database Connection and Session Management."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from app.config import settings

logger = logging.getLogger(__name__)

_admin_engine: Engine | None = None
_readonly_engine: Engine | None = None


def get_engine(readonly: bool = True) -> Engine:
    """Create or return cached SQLAlchemy engine with connection safety parameters."""
    global _admin_engine, _readonly_engine

    if readonly and _readonly_engine is not None:
        return _readonly_engine
    if not readonly and _admin_engine is not None:
        return _admin_engine

    db_url = settings.get_database_url(readonly=readonly)

    connect_args = {}
    if db_url.startswith("postgresql"):
        # Enforce server-side statement timeout to prevent runaway queries
        timeout_sec = settings.STATEMENT_TIMEOUT_MS / 1000.0
        connect_args["options"] = f"-c statement_timeout={settings.STATEMENT_TIMEOUT_MS}"
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        try:
            with engine.connect() as test_conn:
                test_conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning("PostgreSQL unreachable (%s). Auto-fallback to SQLite warehouse.", e)
            settings.DB_TYPE = "sqlite"
            return get_engine(readonly=readonly)
    else:
        # SQLite configuration
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 15
        sqlite_file = Path(settings.SQLITE_DB_PATH)
        if not sqlite_file.exists():
            try:
                from app.db.loader import load_data_warehouse
                logger.info("SQLite database %s not found. Initializing warehouse...", sqlite_file)
                load_data_warehouse(target="sqlite")
            except Exception as e:
                logger.warning("Auto-init of SQLite warehouse encountered: %s", e)
        engine = create_engine(db_url, connect_args=connect_args)

    if readonly:
        _readonly_engine = engine
    else:
        _admin_engine = engine

    return engine


@contextmanager
def get_db_connection(readonly: bool = True) -> Generator[Connection, None, None]:
    """Provide transactional connection context manager."""
    engine = get_engine(readonly=readonly)
    with engine.connect() as conn:
        yield conn


def check_database_health() -> dict[str, str | bool]:
    """Health check for database connectivity."""
    try:
        engine = get_engine(readonly=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": settings.DB_TYPE, "connected": True}
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return {"status": "unhealthy", "database": settings.DB_TYPE, "connected": False, "error": str(e)}
