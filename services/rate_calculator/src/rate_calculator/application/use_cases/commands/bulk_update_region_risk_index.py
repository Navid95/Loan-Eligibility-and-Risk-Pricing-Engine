from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.exceptions import NotFoundError
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.domain.value_objects import Multiplier


@dataclass(frozen=True)
class BulkUpdateRegionRiskIndexCommand:
    region2: str
    new_multiplier: Decimal


class BulkUpdateRegionRiskIndexUseCase:
    def __init__(
        self, *, district_risk_config_repo: DistrictRiskConfigRepository
    ) -> None:
        self._repo = district_risk_config_repo

    async def execute(self, command: BulkUpdateRegionRiskIndexCommand) -> int:
        configs = await self._repo.list_by_region2(command.region2)
        if not configs:
            raise NotFoundError(
                reason=f"no districts found for region '{command.region2}'"
            )

        new_multiplier = Multiplier(command.new_multiplier)
        for config in configs:
            config.update_risk_index(new_multiplier)

        await self._repo.save_many(configs)
        return len(configs)
