from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)


@dataclass(frozen=True)
class CreditTierConfigResult:
    tier: str
    multiplier: Decimal


class ListCreditTierConfigsUseCase:
    def __init__(self, *, credit_tier_config_repo: CreditTierConfigRepository) -> None:
        self._repo = credit_tier_config_repo

    async def execute(self) -> list[CreditTierConfigResult]:
        configs = await self._repo.list_all()
        return [
            CreditTierConfigResult(tier=c.tier.value, multiplier=c.multiplier.value)
            for c in configs
        ]
