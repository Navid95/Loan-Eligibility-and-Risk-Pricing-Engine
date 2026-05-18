from decimal import Decimal
from uuid import uuid4

import pytest
from rate_calculator.domain.aggregates.system_rate_config import SystemRateConfig
from rate_calculator.domain.value_objects.rate import Rate
from rate_calculator.infrastructure.repositories.system_rate_config_repository import (
    SqlAlchemySystemRateConfigRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


class TestSqlAlchemySystemRateConfigRepository:
    async def test_save_and_get(self, session: AsyncSession) -> None:
        repo = SqlAlchemySystemRateConfigRepository(session)
        config = SystemRateConfig(id=uuid4(), base_rate=Rate(Decimal("5.5")))

        await repo.save(config)
        retrieved = await repo.get()

        assert retrieved.id == config.id
        assert retrieved.base_rate == Rate(Decimal("5.5"))

    async def test_save_updates_existing(self, session: AsyncSession) -> None:
        repo = SqlAlchemySystemRateConfigRepository(session)
        config = SystemRateConfig(id=uuid4(), base_rate=Rate(Decimal("5.0")))
        await repo.save(config)

        config.update_base_rate(Rate(Decimal("7.5")))
        await repo.save(config)

        retrieved = await repo.get()
        assert retrieved.base_rate == Rate(Decimal("7.5"))

    async def test_get_raises_when_no_row_seeded(self, session: AsyncSession) -> None:
        repo = SqlAlchemySystemRateConfigRepository(session)
        with pytest.raises(RuntimeError, match="not seeded"):
            await repo.get()
