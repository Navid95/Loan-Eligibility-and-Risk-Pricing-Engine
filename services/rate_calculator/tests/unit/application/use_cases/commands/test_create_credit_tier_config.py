from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.exceptions import ConflictError, ValidationError
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.use_cases.commands.create_credit_tier_config import (
    CreateCreditTierConfigCommand,
    CreateCreditTierConfigUseCase,
)
from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@pytest.fixture
def credit_tier_config_repo() -> AsyncMock:
    return AsyncMock(spec=CreditTierConfigRepository)


@pytest.fixture
def use_case(credit_tier_config_repo: AsyncMock) -> CreateCreditTierConfigUseCase:
    return CreateCreditTierConfigUseCase(
        credit_tier_config_repo=credit_tier_config_repo
    )


class TestCreateCreditTierConfigUseCase:
    async def test_saves_new_config_when_not_existing(
        self,
        use_case: CreateCreditTierConfigUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        credit_tier_config_repo.get.return_value = None
        await use_case.execute(
            CreateCreditTierConfigCommand(tier="A", multiplier=Decimal("1.2"))
        )
        credit_tier_config_repo.save.assert_called_once()

    async def test_saved_config_has_correct_tier_and_multiplier(
        self,
        use_case: CreateCreditTierConfigUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        credit_tier_config_repo.get.return_value = None
        await use_case.execute(
            CreateCreditTierConfigCommand(tier="B", multiplier=Decimal("1.5"))
        )
        saved: CreditTierConfig = credit_tier_config_repo.save.call_args[0][0]
        assert saved.tier == CreditTier.B
        assert saved.multiplier == Multiplier(Decimal("1.5"))

    async def test_raises_conflict_when_config_already_exists(
        self,
        use_case: CreateCreditTierConfigUseCase,
        credit_tier_config_repo: AsyncMock,
    ) -> None:
        credit_tier_config_repo.get.return_value = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )
        with pytest.raises(ConflictError):
            await use_case.execute(
                CreateCreditTierConfigCommand(tier="A", multiplier=Decimal("1.3"))
            )

    async def test_raises_validation_error_for_unknown_tier(
        self, use_case: CreateCreditTierConfigUseCase
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                CreateCreditTierConfigCommand(tier="D", multiplier=Decimal("1.2"))
            )

    @pytest.mark.parametrize("invalid_multiplier", [Decimal("0"), Decimal("-0.5")])
    async def test_raises_domain_error_for_non_positive_multiplier(
        self,
        use_case: CreateCreditTierConfigUseCase,
        credit_tier_config_repo: AsyncMock,
        invalid_multiplier: Decimal,
    ) -> None:
        credit_tier_config_repo.get.return_value = None
        with pytest.raises(DomainError):
            await use_case.execute(
                CreateCreditTierConfigCommand(tier="A", multiplier=invalid_multiplier)
            )
