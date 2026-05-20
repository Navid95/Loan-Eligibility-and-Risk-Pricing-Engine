from datetime import datetime

from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)
from audit_log.domain.aggregates import CalculationRecord


class FakeCalculationRecordRepository(CalculationRecordRepository):
    def __init__(self) -> None:
        self._records: list[CalculationRecord] = []

    def seed(self, *records: CalculationRecord) -> None:
        self._records.extend(records)

    async def save(self, record: CalculationRecord) -> None:
        if not any(r.correlation_id == record.correlation_id for r in self._records):
            self._records.append(record)

    async def list_by_date_range(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        page: int,
        page_size: int,
    ) -> tuple[list[CalculationRecord], int]:
        matching = [r for r in self._records if from_dt <= r.calculated_at <= to_dt]
        matching.sort(key=lambda r: r.calculated_at, reverse=True)
        total = len(matching)
        offset = (page - 1) * page_size
        return matching[offset : offset + page_size], total
