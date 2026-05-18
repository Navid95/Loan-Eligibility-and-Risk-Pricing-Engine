from decimal import Decimal
from uuid import uuid4

import pytest
from rate_calculator.domain.aggregates import SystemRateConfig
from rate_calculator.domain.value_objects import Rate


@pytest.fixture
def system_rate_config() -> SystemRateConfig:
    return SystemRateConfig(id=uuid4(), base_rate=Rate(Decimal("5.0")))


class TestSystemRateConfig:
    def test_update_base_rate_sets_new_rate(
        self, system_rate_config: SystemRateConfig
    ) -> None:
        new_rate = Rate(Decimal("6.0"))
        system_rate_config.update_base_rate(new_rate)
        assert system_rate_config.base_rate == new_rate
