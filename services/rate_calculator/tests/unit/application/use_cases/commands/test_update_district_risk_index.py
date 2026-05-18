from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.use_cases.commands.update_district_risk_index import (
    UpdateDistrictRiskIndexCommand,
    UpdateDistrictRiskIndexUseCase,
)
from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import District, Multiplier


@pytest.fixture
def district_risk_config_repo() -> AsyncMock:
    return AsyncMock(spec=DistrictRiskConfigRepository)


@pytest.fixture
def use_case(district_risk_config_repo: AsyncMock) -> UpdateDistrictRiskIndexUseCase:
    return UpdateDistrictRiskIndexUseCase(
        district_risk_config_repo=district_risk_config_repo
    )


class TestUpdateDistrictRiskIndexUseCase:
    async def test_updates_risk_index_on_config(
        self,
        use_case: UpdateDistrictRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        config = DistrictRiskConfig(
            district=District("München"), multiplier=Multiplier(Decimal("1.1"))
        )
        district_risk_config_repo.get.return_value = config
        await use_case.execute(
            UpdateDistrictRiskIndexCommand(
                district="München", new_multiplier=Decimal("1.4")
            )
        )
        assert config.multiplier == Multiplier(Decimal("1.4"))

    async def test_saves_updated_config(
        self,
        use_case: UpdateDistrictRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        config = DistrictRiskConfig(
            district=District("München"), multiplier=Multiplier(Decimal("1.1"))
        )
        district_risk_config_repo.get.return_value = config
        await use_case.execute(
            UpdateDistrictRiskIndexCommand(
                district="München", new_multiplier=Decimal("1.4")
            )
        )
        district_risk_config_repo.save.assert_called_once_with(config)

    async def test_raises_not_found_when_config_missing(
        self,
        use_case: UpdateDistrictRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            await use_case.execute(
                UpdateDistrictRiskIndexCommand(
                    district="München", new_multiplier=Decimal("1.4")
                )
            )

    async def test_raises_domain_error_for_blank_district_name(
        self, use_case: UpdateDistrictRiskIndexUseCase
    ) -> None:
        with pytest.raises(DomainError):
            await use_case.execute(
                UpdateDistrictRiskIndexCommand(
                    district="   ", new_multiplier=Decimal("1.4")
                )
            )

    @pytest.mark.parametrize("invalid_multiplier", [Decimal("0"), Decimal("-0.5")])
    async def test_raises_domain_error_for_non_positive_multiplier(
        self,
        use_case: UpdateDistrictRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
        invalid_multiplier: Decimal,
    ) -> None:
        district_risk_config_repo.get.return_value = DistrictRiskConfig(
            district=District("München"), multiplier=Multiplier(Decimal("1.1"))
        )
        with pytest.raises(DomainError):
            await use_case.execute(
                UpdateDistrictRiskIndexCommand(
                    district="München", new_multiplier=invalid_multiplier
                )
            )
