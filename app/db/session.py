"""Postgres engine/session factory (Supabase or any standard Postgres host).

Connection is established lazily on first use, not at import time, so this
module can be imported without DATABASE_URL set (e.g. by tools/tests that
don't touch the database).

Required env var: DATABASE_URL - a standard SQLAlchemy Postgres URL, e.g.
    postgresql+psycopg://user:pass@host:6543/dbname?sslmode=require
(Supabase's dashboard gives you this under Connect > Connection String - use
the "Transaction pooler" or "Session pooler" string, not "Direct connection":
Supabase's direct-connection host is IPv6-only, which many hosts (e.g.
Render's free tier) can't route to at all - the pooler is IPv4-compatible.)

`prepare_threshold=None` disables psycopg's server-side prepared-statement
cache: under transaction-mode pooling, consecutive queries on one logical
connection can land on different backend connections, so a statement
prepared on one backend won't exist on the next - server-side prepare must
stay off. Harmless (and unnecessary) under session pooling/direct too.
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
        connect_args={"prepare_threshold": None},
    )


@lru_cache
def _get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Session:
    """New Session bound to the process-wide engine. Caller closes it."""
    return _get_session_factory()()
