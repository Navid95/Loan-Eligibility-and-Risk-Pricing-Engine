from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.domain.aggregates.credit_tier_config import CreditTierConfig
from rate_calculator.domain.value_objects.credit_tier import CreditTier
from rate_calculator.domain.value_objects.multiplier import Multiplier
from rate_calculator.infrastructure.database.models import CreditTierConfigModel


class SqlAlchemyCreditTierConfigRepository(CreditTierConfigRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tier: CreditTier) -> CreditTierConfig | None:
        result = await self._session.execute(
            select(CreditTierConfigModel).where(
                CreditTierConfigModel.tier == tier.value
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return CreditTierConfig(
            tier=CreditTier(row.tier), multiplier=Multiplier(row.multiplier)
        )

    async def list_all(self) -> list[CreditTierConfig]:
        result = await self._session.execute(
            select(CreditTierConfigModel).order_by(CreditTierConfigModel.tier)
        )
        return [
            CreditTierConfig(
                tier=CreditTier(row.tier), multiplier=Multiplier(row.multiplier)
            )
            for row in result.scalars()
        ]

    async def save(self, config: CreditTierConfig) -> None:
        stmt = (
            insert(CreditTierConfigModel)
            .values(tier=config.tier.value, multiplier=config.multiplier.value)
            .on_conflict_do_update(
                index_elements=["tier"],
                set_={"multiplier": config.multiplier.value},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
