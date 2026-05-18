from decimal import Decimal

import pytest
from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.value_objects import CreditTier, Multiplier


@pytest.fixture
def credit_tier_config() -> CreditTierConfig:
    return CreditTierConfig(tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2")))


class TestCreditTierConfig:
    def test_update_multiplier_sets_new_multiplier(
        self, credit_tier_config: CreditTierConfig
    ) -> None:
        new_multiplier = Multiplier(Decimal("1.5"))
        credit_tier_config.update_multiplier(new_multiplier)
        assert credit_tier_config.multiplier == new_multiplier
