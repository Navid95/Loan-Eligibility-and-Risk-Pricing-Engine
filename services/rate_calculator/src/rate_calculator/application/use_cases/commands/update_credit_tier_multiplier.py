from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.exceptions import NotFoundError, ValidationError
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@dataclass(frozen=True)
class UpdateCreditTierMultiplierCommand:
    tier: str
    new_multiplier: Decimal


class UpdateCreditTierMultiplierUseCase:
    def __init__(self, *, credit_tier_config_repo: CreditTierConfigRepository) -> None:
        self._repo = credit_tier_config_repo

    async def execute(self, command: UpdateCreditTierMultiplierCommand) -> None:
        try:
            tier = CreditTier(command.tier)
        except ValueError:
            raise ValidationError(reason=f"'{command.tier}' is not a valid credit tier")

        config = await self._repo.get(tier)
        if config is None:
            raise NotFoundError(
                reason=f"credit tier config for '{tier.value}' not found"
            )

        config.update_multiplier(Multiplier(command.new_multiplier))
        await self._repo.save(config)
