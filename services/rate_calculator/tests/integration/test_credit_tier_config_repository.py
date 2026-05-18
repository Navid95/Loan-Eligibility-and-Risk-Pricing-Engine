from decimal import Decimal

from rate_calculator.domain.aggregates.credit_tier_config import CreditTierConfig
from rate_calculator.domain.value_objects.credit_tier import CreditTier
from rate_calculator.domain.value_objects.multiplier import Multiplier
from rate_calculator.infrastructure.repositories.credit_tier_config_repository import (
    SqlAlchemyCreditTierConfigRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


class TestSqlAlchemyCreditTierConfigRepository:
    async def test_save_and_get(self, session: AsyncSession) -> None:
        repo = SqlAlchemyCreditTierConfigRepository(session)
        config = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )

        await repo.save(config)
        retrieved = await repo.get(CreditTier.A)

        assert retrieved is not None
        assert retrieved.tier == CreditTier.A
        assert retrieved.multiplier == Multiplier(Decimal("1.2"))

    async def test_get_returns_none_for_missing_tier(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCreditTierConfigRepository(session)
        result = await repo.get(CreditTier.B)
        assert result is None

    async def test_save_updates_existing(self, session: AsyncSession) -> None:
        repo = SqlAlchemyCreditTierConfigRepository(session)
        config = CreditTierConfig(
            tier=CreditTier.C, multiplier=Multiplier(Decimal("0.9"))
        )
        await repo.save(config)

        config.update_multiplier(Multiplier(Decimal("1.5")))
        await repo.save(config)

        retrieved = await repo.get(CreditTier.C)
        assert retrieved is not None
        assert retrieved.multiplier == Multiplier(Decimal("1.5"))

    async def test_list_all_returns_all_saved_tiers(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCreditTierConfigRepository(session)
        for tier, value in [
            (CreditTier.A, "1.1"),
            (CreditTier.B, "1.0"),
            (CreditTier.C, "0.8"),
        ]:
            await repo.save(
                CreditTierConfig(tier=tier, multiplier=Multiplier(Decimal(value)))
            )

        results = await repo.list_all()

        assert len(results) == 3
        tiers = {r.tier for r in results}
        assert tiers == {CreditTier.A, CreditTier.B, CreditTier.C}
