from decimal import Decimal

import pytest
from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.value_objects import District, Multiplier


@pytest.fixture
def district_risk_config() -> DistrictRiskConfig:
    return DistrictRiskConfig(
        district=District("München"), multiplier=Multiplier(Decimal("1.1"))
    )


class TestDistrictRiskConfig:
    def test_update_risk_index_sets_new_multiplier(
        self, district_risk_config: DistrictRiskConfig
    ) -> None:
        new_multiplier = Multiplier(Decimal("1.4"))
        district_risk_config.update_risk_index(new_multiplier)
        assert district_risk_config.multiplier == new_multiplier
