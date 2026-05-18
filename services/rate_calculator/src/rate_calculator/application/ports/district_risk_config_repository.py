from abc import ABC, abstractmethod

from rate_calculator.domain.aggregates import DistrictRiskConfig
from rate_calculator.domain.value_objects import District


class DistrictRiskConfigRepository(ABC):
    @abstractmethod
    async def get(self, district: District) -> DistrictRiskConfig | None: ...

    @abstractmethod
    async def list_all(
        self, *, page: int, page_size: int
    ) -> tuple[list[DistrictRiskConfig], int]: ...

    @abstractmethod
    async def list_by_region2(self, region2: str) -> list[DistrictRiskConfig]: ...

    @abstractmethod
    async def save(self, config: DistrictRiskConfig) -> None: ...

    @abstractmethod
    async def save_many(self, configs: list[DistrictRiskConfig]) -> None: ...
