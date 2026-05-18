from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.domain.aggregates.system_rate_config import SystemRateConfig
from rate_calculator.domain.value_objects.rate import Rate
from rate_calculator.infrastructure.database.models import SystemRateConfigModel


class SqlAlchemySystemRateConfigRepository(SystemRateConfigRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SystemRateConfig:
        result = await self._session.execute(select(SystemRateConfigModel).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            raise RuntimeError("system_rate_config not seeded")
        return SystemRateConfig(id=row.id, base_rate=Rate(row.base_rate))

    async def save(self, config: SystemRateConfig) -> None:
        row = await self._session.get(SystemRateConfigModel, config.id)
        if row is None:
            row = SystemRateConfigModel(id=config.id, base_rate=config.base_rate.value)
            self._session.add(row)
        else:
            row.base_rate = config.base_rate.value
        await self._session.flush()
