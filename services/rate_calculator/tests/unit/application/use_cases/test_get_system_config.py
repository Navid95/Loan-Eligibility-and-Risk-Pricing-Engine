from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.application.use_cases.get_system_config import (
    GetSystemConfigUseCase,
    SystemConfigResult,
)
from rate_calculator.domain.aggregates import SystemRateConfig
from rate_calculator.domain.value_objects import Rate


@pytest.fixture
def system_rate_config_repo() -> AsyncMock:
    return AsyncMock(spec=SystemRateConfigRepository)


@pytest.fixture
def use_case(system_rate_config_repo: AsyncMock) -> GetSystemConfigUseCase:
    return GetSystemConfigUseCase(system_rate_config_repo=system_rate_config_repo)


class TestGetSystemConfigUseCase:
    async def test_returns_current_base_rate(
        self, use_case: GetSystemConfigUseCase, system_rate_config_repo: AsyncMock
    ) -> None:
        system_rate_config_repo.get.return_value = SystemRateConfig(
            id=uuid4(), base_rate=Rate(Decimal("4.5"))
        )
        result = await use_case.execute()
        assert result == SystemConfigResult(base_rate=Decimal("4.5"))
