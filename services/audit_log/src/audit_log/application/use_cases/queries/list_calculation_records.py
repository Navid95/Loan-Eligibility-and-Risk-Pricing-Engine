from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from audit_log.application.exceptions import ValidationError
from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)

_MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class ListCalculationRecordsQuery:
    from_dt: datetime
    to_dt: datetime
    page: int
    page_size: int


@dataclass(frozen=True)
class CalculationRecordResult:
    correlation_id: UUID
    credit_tier: str
    district: str
    base_rate: Decimal
    term_multiplier: Decimal
    credit_tier_multiplier: Decimal
    regional_risk_multiplier: Decimal
    final_rate: Decimal
    calculated_at: datetime
    recorded_at: datetime


@dataclass(frozen=True)
class PagedCalculationRecordsResult:
    items: list[CalculationRecordResult]
    total: int
    page: int
    page_size: int


class ListCalculationRecordsUseCase:
    def __init__(self, *, repo: CalculationRecordRepository) -> None:
        self._repo = repo

    async def execute(
        self, query: ListCalculationRecordsQuery
    ) -> PagedCalculationRecordsResult:
        if query.from_dt >= query.to_dt:
            raise ValidationError(reason="'from' must be earlier than 'to'")
        if query.page < 1:
            raise ValidationError(reason="'page' must be at least 1")
        if not (1 <= query.page_size <= _MAX_PAGE_SIZE):
            raise ValidationError(
                reason=f"'page_size' must be between 1 and {_MAX_PAGE_SIZE}"
            )

        records, total = await self._repo.list_by_date_range(
            from_dt=query.from_dt,
            to_dt=query.to_dt,
            page=query.page,
            page_size=query.page_size,
        )
        items = [
            CalculationRecordResult(
                correlation_id=r.correlation_id,
                credit_tier=r.credit_tier.value,
                district=r.district.name,
                base_rate=r.base_rate.value,
                term_multiplier=r.term_multiplier.value,
                credit_tier_multiplier=r.credit_tier_multiplier.value,
                regional_risk_multiplier=r.regional_risk_multiplier.value,
                final_rate=r.final_rate.value,
                calculated_at=r.calculated_at,
                recorded_at=r.recorded_at,
            )
            for r in records
        ]
        return PagedCalculationRecordsResult(
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
