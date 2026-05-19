from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from audit_log.api.dependencies import get_calculation_record_repo
from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)
from audit_log.application.use_cases.queries.list_calculation_records import (
    ListCalculationRecordsQuery,
    ListCalculationRecordsUseCase,
    PagedCalculationRecordsResult,
)

router = APIRouter(prefix="/records", tags=["records"])


class CalculationRecordResponse(BaseModel):
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


class PagedRecordsResponse(BaseModel):
    items: list[CalculationRecordResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=PagedRecordsResponse)
async def list_records(
    from_dt: datetime = Query(alias="from"),
    to_dt: datetime = Query(alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    repo: CalculationRecordRepository = Depends(get_calculation_record_repo),
) -> PagedRecordsResponse:
    use_case = ListCalculationRecordsUseCase(repo=repo)
    result: PagedCalculationRecordsResult = await use_case.execute(
        ListCalculationRecordsQuery(
            from_dt=from_dt,
            to_dt=to_dt,
            page=page,
            page_size=page_size,
        )
    )
    return PagedRecordsResponse(
        items=[
            CalculationRecordResponse(
                correlation_id=item.correlation_id,
                credit_tier=item.credit_tier,
                district=item.district,
                base_rate=item.base_rate,
                term_multiplier=item.term_multiplier,
                credit_tier_multiplier=item.credit_tier_multiplier,
                regional_risk_multiplier=item.regional_risk_multiplier,
                final_rate=item.final_rate,
                calculated_at=item.calculated_at,
                recorded_at=item.recorded_at,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
