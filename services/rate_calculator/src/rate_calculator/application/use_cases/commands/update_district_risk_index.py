from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.domain.value_objects import District, Multiplier


@dataclass(frozen=True)
class UpdateDistrictRiskIndexCommand:
    district: str
    new_multiplier: Decimal


class UpdateDistrictRiskIndexUseCase:
    def __init__(
        self, *, district_risk_config_repo: DistrictRiskConfigRepository
    ) -> None:
        self._repo = district_risk_config_repo

    async def execute(self, command: UpdateDistrictRiskIndexCommand) -> None:
        district = District(command.district)

        config = await self._repo.get(district)
        if config is None:
            raise NotFoundError(
                reason=f"district risk config for '{district.name}' not found"
            )

        config.update_risk_index(Multiplier(command.new_multiplier))
        await self._repo.save(config)
