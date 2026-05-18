from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.domain.value_objects import Rate


@dataclass(frozen=True)
class UpdateBaseRateCommand:
    new_rate: Decimal


class UpdateBaseRateUseCase:
    def __init__(self, *, system_rate_config_repo: SystemRateConfigRepository) -> None:
        self._repo = system_rate_config_repo

    async def execute(self, command: UpdateBaseRateCommand) -> None:
        config = await self._repo.get()
        config.update_base_rate(Rate(command.new_rate))
        await self._repo.save(config)
