from logging.config import fileConfig

from dotenv import load_dotenv

from alembic import context

load_dotenv()

from app.db.models import Base  # noqa: E402
from app.db.session import get_engine  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Not supported: this project always migrates through a live connection
    (see app/db/session.py)."""
    raise RuntimeError(
        "Offline migrations aren't supported - run 'alembic upgrade head' "
        "with DATABASE_URL set instead."
    )


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
