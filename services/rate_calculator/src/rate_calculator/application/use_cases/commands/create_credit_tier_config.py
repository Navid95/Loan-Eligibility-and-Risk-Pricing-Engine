from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.exceptions import ConflictError, ValidationError
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@dataclass(frozen=True)
class CreateCreditTierConfigCommand:
    tier: str
    multiplier: Decimal


class CreateCreditTierConfigUseCase:
    def __init__(self, *, credit_tier_config_repo: CreditTierConfigRepository) -> None:
        self._repo = credit_tier_config_repo

    async def execute(self, command: CreateCreditTierConfigCommand) -> None:
        try:
            tier = CreditTier(command.tier)
        except ValueError:
            raise ValidationError(reason=f"'{command.tier}' is not a valid credit tier")

        existing = await self._repo.get(tier)
        if existing is not None:
            raise ConflictError(
                reason=f"credit tier config for '{tier.value}' already exists"
            )

        config = CreditTierConfig(tier=tier, multiplier=Multiplier(command.multiplier))
        await self._repo.save(config)
