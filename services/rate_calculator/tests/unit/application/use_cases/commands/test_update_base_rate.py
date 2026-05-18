from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.application.use_cases.commands.update_base_rate import (
    UpdateBaseRateCommand,
    UpdateBaseRateUseCase,
)
from rate_calculator.domain.aggregates import SystemRateConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import Rate


@pytest.fixture
def system_rate_config_repo() -> AsyncMock:
    return AsyncMock(spec=SystemRateConfigRepository)


@pytest.fixture
def use_case(system_rate_config_repo: AsyncMock) -> UpdateBaseRateUseCase:
    return UpdateBaseRateUseCase(system_rate_config_repo=system_rate_config_repo)


class TestUpdateBaseRateUseCase:
    async def test_updates_base_rate_on_config(
        self, use_case: UpdateBaseRateUseCase, system_rate_config_repo: AsyncMock
    ) -> None:
        config = SystemRateConfig(id=uuid4(), base_rate=Rate(Decimal("5.0")))
        system_rate_config_repo.get.return_value = config
        await use_case.execute(UpdateBaseRateCommand(new_rate=Decimal("7.5")))
        assert config.base_rate == Rate(Decimal("7.5"))

    async def test_saves_updated_config(
        self, use_case: UpdateBaseRateUseCase, system_rate_config_repo: AsyncMock
    ) -> None:
        config = SystemRateConfig(id=uuid4(), base_rate=Rate(Decimal("5.0")))
        system_rate_config_repo.get.return_value = config
        await use_case.execute(UpdateBaseRateCommand(new_rate=Decimal("7.5")))
        system_rate_config_repo.save.assert_called_once_with(config)

    @pytest.mark.parametrize("invalid_rate", [Decimal("0"), Decimal("-1.0")])
    async def test_raises_domain_error_for_non_positive_rate(
        self,
        use_case: UpdateBaseRateUseCase,
        system_rate_config_repo: AsyncMock,
        invalid_rate: Decimal,
    ) -> None:
        system_rate_config_repo.get.return_value = SystemRateConfig(
            id=uuid4(), base_rate=Rate(Decimal("5.0"))
        )
        with pytest.raises(DomainError):
            await use_case.execute(UpdateBaseRateCommand(new_rate=invalid_rate))
