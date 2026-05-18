from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.exceptions import NotFoundError, ValidationError
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.use_cases.commands.update_credit_tier_multiplier import (  # noqa: E501
    UpdateCreditTierMultiplierCommand,
    UpdateCreditTierMultiplierUseCase,
)
from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@pytest.fixture
def credit_tier_config_repo() -> AsyncMock:
    return AsyncMock(spec=CreditTierConfigRepository)


@pytest.fixture
def use_case(credit_tier_config_repo: AsyncMock) -> UpdateCreditTierMultiplierUseCase:
    return UpdateCreditTierMultiplierUseCase(
        credit_tier_config_repo=credit_tier_config_repo
    )


class TestUpdateCreditTierMultiplierUseCase:
    async def test_updates_multiplier_on_config(
        self,
        use_case: UpdateCreditTierMultiplierUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        config = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )
        credit_tier_config_repo.get.return_value = config
        await use_case.execute(
            UpdateCreditTierMultiplierCommand(tier="A", new_multiplier=Decimal("1.5"))
        )
        assert config.multiplier == Multiplier(Decimal("1.5"))

    async def test_saves_updated_config(
        self,
        use_case: UpdateCreditTierMultiplierUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        config = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )
        credit_tier_config_repo.get.return_value = config
        await use_case.execute(
            UpdateCreditTierMultiplierCommand(tier="A", new_multiplier=Decimal("1.5"))
        )
        credit_tier_config_repo.save.assert_called_once_with(config)

    async def test_raises_not_found_when_config_missing(
        self,
        use_case: UpdateCreditTierMultiplierUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        credit_tier_config_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            await use_case.execute(
                UpdateCreditTierMultiplierCommand(
                    tier="A", new_multiplier=Decimal("1.5")
                )
            )

    async def test_raises_validation_error_for_unknown_tier(
        self, use_case: UpdateCreditTierMultiplierUseCase
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                UpdateCreditTierMultiplierCommand(
                    tier="D", new_multiplier=Decimal("1.5")
                )
            )

    @pytest.mark.parametrize("invalid_multiplier", [Decimal("0"), Decimal("-0.5")])
    async def test_raises_domain_error_for_non_positive_multiplier(
        self,
        use_case: UpdateCreditTierMultiplierUseCase,
        credit_tier_config_repo: AsyncMock,
        invalid_multiplier: Decimal,
    ) -> None:
        credit_tier_config_repo.get.return_value = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )
        with pytest.raises(DomainError):
            await use_case.execute(
                UpdateCreditTierMultiplierCommand(
                    tier="A", new_multiplier=invalid_multiplier
                )
            )
