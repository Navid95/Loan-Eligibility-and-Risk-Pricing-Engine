from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)


@dataclass(frozen=True)
class SystemConfigResult:
    base_rate: Decimal


class GetSystemConfigUseCase:
    def __init__(self, *, system_rate_config_repo: SystemRateConfigRepository) -> None:
        self._repo = system_rate_config_repo

    async def execute(self) -> SystemConfigResult:
        config = await self._repo.get()
        return SystemConfigResult(base_rate=config.base_rate.value)
