import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from audit_log.infrastructure.database.engine import (
    create_engine,
    create_session_factory,
)
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer

_ALEMBIC_INI = Path(__file__).parent.parent.parent / "alembic.ini"


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
def apply_migrations(db_url: str) -> None:
    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "RABBITMQ_URL": "amqp://localhost",
    }
    original_environ = os.environ.copy()
    os.environ.update(env)
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        os.environ.clear()
        os.environ.update(original_environ)


@pytest.fixture
async def session(
    db_url: str, apply_migrations: None
) -> AsyncGenerator[AsyncSession, None]:
    # Fresh engine per test so asyncpg connections are bound to the current
    # event loop — avoids cross-loop errors with function-scoped pytest-asyncio.
    engine = create_engine(db_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as s:
        async with s.begin():
            yield s
            await s.rollback()
    await engine.dispose()
