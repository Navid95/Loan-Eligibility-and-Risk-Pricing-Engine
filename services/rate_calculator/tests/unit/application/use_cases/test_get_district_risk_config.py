from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.use_cases.get_district_risk_config import (
    DistrictRiskConfigResult,
    GetDistrictRiskConfigQuery,
    GetDistrictRiskConfigUseCase,
)
from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import District, Multiplier


@pytest.fixture
def district_risk_config_repo() -> AsyncMock:
    return AsyncMock(spec=DistrictRiskConfigRepository)


@pytest.fixture
def use_case(district_risk_config_repo: AsyncMock) -> GetDistrictRiskConfigUseCase:
    return GetDistrictRiskConfigUseCase(
        district_risk_config_repo=district_risk_config_repo
    )


class TestGetDistrictRiskConfigUseCase:
    async def test_returns_district_config(
        self,
        use_case: GetDistrictRiskConfigUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.get.return_value = DistrictRiskConfig(
            district=District("München"), multiplier=Multiplier(Decimal("1.1"))
        )
        result = await use_case.execute(GetDistrictRiskConfigQuery(district="München"))
        assert result == DistrictRiskConfigResult(
            district="München", multiplier=Decimal("1.1")
        )

    async def test_raises_not_found_when_config_missing(
        self,
        use_case: GetDistrictRiskConfigUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            await use_case.execute(GetDistrictRiskConfigQuery(district="München"))

    async def test_raises_domain_error_for_blank_district_name(
        self, use_case: GetDistrictRiskConfigUseCase
    ) -> None:
        with pytest.raises(DomainError):
            await use_case.execute(GetDistrictRiskConfigQuery(district="  "))
