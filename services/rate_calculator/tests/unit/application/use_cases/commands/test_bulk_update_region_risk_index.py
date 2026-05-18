from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.use_cases.commands.bulk_update_region_risk_index import (  # noqa: E501
    BulkUpdateRegionRiskIndexCommand,
    BulkUpdateRegionRiskIndexUseCase,
)
from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import District, Multiplier


@pytest.fixture
def district_risk_config_repo() -> AsyncMock:
    return AsyncMock(spec=DistrictRiskConfigRepository)


@pytest.fixture
def use_case(district_risk_config_repo: AsyncMock) -> BulkUpdateRegionRiskIndexUseCase:
    return BulkUpdateRegionRiskIndexUseCase(
        district_risk_config_repo=district_risk_config_repo
    )


def _make_configs(names: list[str]) -> list[DistrictRiskConfig]:
    return [
        DistrictRiskConfig(
            district=District(name), multiplier=Multiplier(Decimal("1.0"))
        )
        for name in names
    ]


class TestBulkUpdateRegionRiskIndexUseCase:
    async def test_updates_all_district_configs_in_region2(
        self,
        use_case: BulkUpdateRegionRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        configs = _make_configs(["München", "Schwabing", "Maxvorstadt"])
        district_risk_config_repo.list_by_region2.return_value = configs
        await use_case.execute(
            BulkUpdateRegionRiskIndexCommand(
                region2="Oberbayern", new_multiplier=Decimal("1.3")
            )
        )
        for config in configs:
            assert config.multiplier == Multiplier(Decimal("1.3"))

    async def test_saves_all_updated_configs(
        self,
        use_case: BulkUpdateRegionRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        configs = _make_configs(["München", "Schwabing"])
        district_risk_config_repo.list_by_region2.return_value = configs
        await use_case.execute(
            BulkUpdateRegionRiskIndexCommand(
                region2="Oberbayern", new_multiplier=Decimal("1.3")
            )
        )
        district_risk_config_repo.save_many.assert_called_once_with(configs)

    async def test_returns_count_of_updated_districts(
        self,
        use_case: BulkUpdateRegionRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.list_by_region2.return_value = _make_configs(
            ["München", "Schwabing", "Maxvorstadt"]
        )
        count = await use_case.execute(
            BulkUpdateRegionRiskIndexCommand(
                region2="Oberbayern", new_multiplier=Decimal("1.3")
            )
        )
        assert count == 3

    async def test_raises_not_found_when_no_districts_in_region2(
        self,
        use_case: BulkUpdateRegionRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district_risk_config_repo.list_by_region2.return_value = []
        with pytest.raises(NotFoundError):
            await use_case.execute(
                BulkUpdateRegionRiskIndexCommand(
                    region2="Unknown", new_multiplier=Decimal("1.3")
                )
            )

    @pytest.mark.parametrize("invalid_multiplier", [Decimal("0"), Decimal("-0.5")])
    async def test_raises_domain_error_for_non_positive_multiplier(
        self,
        use_case: BulkUpdateRegionRiskIndexUseCase,
        district_risk_config_repo: AsyncMock,
        invalid_multiplier: Decimal,
    ) -> None:
        district_risk_config_repo.list_by_region2.return_value = _make_configs(
            ["München"]
        )
        with pytest.raises(DomainError):
            await use_case.execute(
                BulkUpdateRegionRiskIndexCommand(
                    region2="Oberbayern", new_multiplier=invalid_multiplier
                )
            )
