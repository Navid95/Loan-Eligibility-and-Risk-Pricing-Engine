from dataclasses import dataclass

from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.use_cases.get_district_risk_config import (
    DistrictRiskConfigResult,
)


@dataclass(frozen=True)
class ListDistrictRiskConfigsQuery:
    page: int
    page_size: int


@dataclass(frozen=True)
class PagedDistrictRiskConfigsResult:
    items: list[DistrictRiskConfigResult]
    total: int
    page: int
    page_size: int


class ListDistrictRiskConfigsUseCase:
    def __init__(
        self, *, district_risk_config_repo: DistrictRiskConfigRepository
    ) -> None:
        self._repo = district_risk_config_repo

    async def execute(
        self, query: ListDistrictRiskConfigsQuery
    ) -> PagedDistrictRiskConfigsResult:
        configs, total = await self._repo.list_all(
            page=query.page, page_size=query.page_size
        )
        items = [
            DistrictRiskConfigResult(
                district=c.district.name, multiplier=c.multiplier.value
            )
            for c in configs
        ]
        return PagedDistrictRiskConfigsResult(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
