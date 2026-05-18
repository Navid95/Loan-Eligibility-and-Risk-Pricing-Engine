from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.domain.value_objects import District


@dataclass(frozen=True)
class GetDistrictRiskConfigQuery:
    district: str


@dataclass(frozen=True)
class DistrictRiskConfigResult:
    district: str
    multiplier: Decimal


class GetDistrictRiskConfigUseCase:
    def __init__(
        self, *, district_risk_config_repo: DistrictRiskConfigRepository
    ) -> None:
        self._repo = district_risk_config_repo

    async def execute(
        self, query: GetDistrictRiskConfigQuery
    ) -> DistrictRiskConfigResult:
        district = District(query.district)

        config = await self._repo.get(district)
        if config is None:
            raise NotFoundError(
                reason=f"district risk config for '{district.name}' not found"
            )

        return DistrictRiskConfigResult(
            district=config.district.name, multiplier=config.multiplier.value
        )
