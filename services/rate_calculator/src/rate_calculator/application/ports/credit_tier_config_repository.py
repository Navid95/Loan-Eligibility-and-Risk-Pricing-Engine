from abc import ABC, abstractmethod

from rate_calculator.domain.aggregates import CreditTierConfig
from rate_calculator.domain.value_objects import CreditTier


class CreditTierConfigRepository(ABC):
    @abstractmethod
    async def get(self, tier: CreditTier) -> CreditTierConfig | None: ...

    @abstractmethod
    async def list_all(self) -> list[CreditTierConfig]: ...

    @abstractmethod
    async def save(self, config: CreditTierConfig) -> None: ...
