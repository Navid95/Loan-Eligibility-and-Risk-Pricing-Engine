from abc import ABC, abstractmethod
from datetime import datetime

from audit_log.domain.aggregates import CalculationRecord


class CalculationRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: CalculationRecord) -> None: ...

    @abstractmethod
    async def list_by_date_range(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        page: int,
        page_size: int,
    ) -> tuple[list[CalculationRecord], int]: ...
