"""Postgres engine/session factory (Supabase or any standard Postgres host).

Connection is established lazily on first use, not at import time, so this
module can be imported without DATABASE_URL set (e.g. by tools/tests that
don't touch the database).

Required env var: DATABASE_URL - a standard SQLAlchemy Postgres URL, e.g.
    postgresql+psycopg://user:pass@host:5432/dbname?sslmode=require
(Supabase's dashboard gives you this under Project Settings > Database >
Connection string - use the "Session pooler" or direct connection string,
psycopg driver, and keep sslmode=require.)
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache
def get_engine() -> Engine:
    """Process-wide engine, created on first use."""
    return create_engine(
        os.environ["DATABASE_URL"],
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )


@lru_cache
def _get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Session:
    """New Session bound to the process-wide engine. Caller closes it."""
    return _get_session_factory()()
