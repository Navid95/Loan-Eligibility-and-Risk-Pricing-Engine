from abc import ABC, abstractmethod

from rate_calculator.domain.events import RateCalculated


class OutboxRepository(ABC):
    @abstractmethod
    async def save(self, event: RateCalculated) -> None: ...
