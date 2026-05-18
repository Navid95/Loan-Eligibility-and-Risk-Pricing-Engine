from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.use_cases.get_district_risk_config import (
    DistrictRiskConfigResult,
)
from rate_calculator.application.use_cases.list_district_risk_configs import (
    ListDistrictRiskConfigsQuery,
    ListDistrictRiskConfigsUseCase,
    PagedDistrictRiskConfigsResult,
)
from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.value_objects import District, Multiplier


@pytest.fixture
def district_risk_config_repo() -> AsyncMock:
    return AsyncMock(spec=DistrictRiskConfigRepository)


@pytest.fixture
def use_case(district_risk_config_repo: AsyncMock) -> ListDistrictRiskConfigsUseCase:
    return ListDistrictRiskConfigsUseCase(
        district_risk_config_repo=district_risk_config_repo
    )


class TestListDistrictRiskConfigsUseCase:
    async def test_returns_paged_results(
        self,
        use_case: ListDistrictRiskConfigsUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        configs = [
            DistrictRiskConfig(
                district=District("München"), multiplier=Multiplier(Decimal("1.1"))
            ),
            DistrictRiskConfig(
                district=District("Nürnberg"), multiplier=Multiplier(Decimal("1.2"))
            ),
        ]
        district_risk_config_repo.list_all.return_value = (configs, 50)
        result = await use_case.execute(
            ListDistrictRiskConfigsQuery(page=1, page_size=20)
        )
        assert result == PagedDistrictRiskConfigsResult(
            items=[
                DistrictRiskConfigResult(district="München", multiplier=Decimal("1.1")),
                DistrictRiskConfigResult(
                    district="Nürnberg", multiplier=Decimal("1.2")
                ),
            ],
            total=50,
            page=1,
            page_size=20,
        )

    async def test_returns_empty_page_when_no_configs(
        self,
        use_case: ListDistrictRiskConfigsUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.list_all.return_value = ([], 0)
        result = await use_case.execute(
            ListDistrictRiskConfigsQuery(page=1, page_size=20)
        )
        assert result == PagedDistrictRiskConfigsResult(
            items=[], total=0, page=1, page_size=20
        )
