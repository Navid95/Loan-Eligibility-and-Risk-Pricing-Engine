from abc import ABC, abstractmethod

from rate_calculator.domain.aggregates import SystemRateConfig


class SystemRateConfigRepository(ABC):
    @abstractmethod
    async def get(self) -> SystemRateConfig: ...

    @abstractmethod
    async def save(self, config: SystemRateConfig) -> None: ...
