from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.use_cases.list_credit_tier_configs import (
    CreditTierConfigResult,
    ListCreditTierConfigsUseCase,
)
from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@pytest.fixture
def credit_tier_config_repo() -> AsyncMock:
    return AsyncMock(spec=CreditTierConfigRepository)


@pytest.fixture
def use_case(credit_tier_config_repo: AsyncMock) -> ListCreditTierConfigsUseCase:
    return ListCreditTierConfigsUseCase(credit_tier_config_repo=credit_tier_config_repo)


class TestListCreditTierConfigsUseCase:
    async def test_returns_all_tier_configs(
        self, use_case: ListCreditTierConfigsUseCase, credit_tier_config_repo: AsyncMock
    ) -> None:
        credit_tier_config_repo.list_all.return_value = [
            CreditTierConfig(tier=CreditTier.A, multiplier=Multiplier(Decimal("1.0"))),
            CreditTierConfig(tier=CreditTier.B, multiplier=Multiplier(Decimal("1.3"))),
            CreditTierConfig(tier=CreditTier.C, multiplier=Multiplier(Decimal("1.7"))),
        ]
        result = await use_case.execute()
        assert result == [
            CreditTierConfigResult(tier="A", multiplier=Decimal("1.0")),
            CreditTierConfigResult(tier="B", multiplier=Decimal("1.3")),
            CreditTierConfigResult(tier="C", multiplier=Decimal("1.7")),
        ]

    async def test_returns_empty_list_when_no_configs(
        self, use_case: ListCreditTierConfigsUseCase, credit_tier_config_repo: AsyncMock
    ) -> None:
        credit_tier_config_repo.list_all.return_value = []
        result = await use_case.execute()
        assert result == []
