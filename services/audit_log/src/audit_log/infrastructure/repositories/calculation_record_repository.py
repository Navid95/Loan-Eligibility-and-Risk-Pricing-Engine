from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)
from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate
from audit_log.infrastructure.database.models import CalculationRecordModel


def _to_domain(row: CalculationRecordModel) -> CalculationRecord:
    return CalculationRecord(
        correlation_id=row.correlation_id,
        credit_tier=CreditTier(row.credit_tier),
        district=District(row.district),
        base_rate=Rate(Decimal(str(row.base_rate))),
        term_multiplier=Multiplier(Decimal(str(row.term_multiplier))),
        credit_tier_multiplier=Multiplier(Decimal(str(row.credit_tier_multiplier))),
        regional_risk_multiplier=Multiplier(Decimal(str(row.regional_risk_multiplier))),
        final_rate=Rate(Decimal(str(row.final_rate))),
        calculated_at=row.calculated_at,
        recorded_at=row.recorded_at,
    )


class SqlAlchemyCalculationRecordRepository(CalculationRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: CalculationRecord) -> None:
        stmt = (
            insert(CalculationRecordModel)
            .values(
                id=record.correlation_id,
                correlation_id=record.correlation_id,
                credit_tier=record.credit_tier.value,
                district=record.district.name,
                base_rate=record.base_rate.value,
                term_multiplier=record.term_multiplier.value,
                credit_tier_multiplier=record.credit_tier_multiplier.value,
                regional_risk_multiplier=record.regional_risk_multiplier.value,
                final_rate=record.final_rate.value,
                calculated_at=record.calculated_at,
                recorded_at=record.recorded_at,
            )
            .on_conflict_do_nothing(index_elements=["correlation_id"])
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_by_date_range(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        page: int,
        page_size: int,
    ) -> tuple[list[CalculationRecord], int]:
        where_clause = (
            CalculationRecordModel.calculated_at >= from_dt,
            CalculationRecordModel.calculated_at <= to_dt,
        )

        count_result = await self._session.execute(
            select(func.count())
            .select_from(CalculationRecordModel)
            .where(*where_clause)
        )
        total: int = count_result.scalar_one()

        rows_result = await self._session.execute(
            select(CalculationRecordModel)
            .where(*where_clause)
            .order_by(CalculationRecordModel.calculated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = rows_result.scalars().all()

        return [_to_domain(row) for row in rows], total
