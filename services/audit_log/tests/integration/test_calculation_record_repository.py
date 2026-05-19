from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate
from audit_log.infrastructure.repositories.calculation_record_repository import (
    SqlAlchemyCalculationRecordRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession

_BASE_TIME = datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)


def _make_record(
    *,
    calculated_at: datetime = _BASE_TIME,
    credit_tier: CreditTier = CreditTier.A,
) -> CalculationRecord:
    return CalculationRecord(
        correlation_id=uuid4(),
        credit_tier=credit_tier,
        district=District("München"),
        base_rate=Rate(Decimal("1.03")),
        term_multiplier=Multiplier(Decimal("1.0")),
        credit_tier_multiplier=Multiplier(Decimal("1.05")),
        regional_risk_multiplier=Multiplier(Decimal("1.0")),
        final_rate=Rate(Decimal("1.0815")),
        calculated_at=calculated_at,
        recorded_at=datetime.now(UTC),
    )


class TestSqlAlchemyCalculationRecordRepositorySave:
    async def test_save_persists_record(self, session: AsyncSession) -> None:
        record = _make_record()
        repo = SqlAlchemyCalculationRecordRepository(session)

        await repo.save(record)

        records, total = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(seconds=1),
            to_dt=_BASE_TIME + timedelta(seconds=1),
            page=1,
            page_size=10,
        )
        assert total == 1
        assert records[0].correlation_id == record.correlation_id

    async def test_save_duplicate_correlation_id_is_idempotent(
        self, session: AsyncSession
    ) -> None:
        record = _make_record()
        repo = SqlAlchemyCalculationRecordRepository(session)

        await repo.save(record)
        await repo.save(record)  # must not raise

        _, total = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(seconds=1),
            to_dt=_BASE_TIME + timedelta(seconds=1),
            page=1,
            page_size=10,
        )
        assert total == 1

    async def test_save_preserves_all_fields(self, session: AsyncSession) -> None:
        record = _make_record(credit_tier=CreditTier.C)
        repo = SqlAlchemyCalculationRecordRepository(session)

        await repo.save(record)

        records, _ = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(seconds=1),
            to_dt=_BASE_TIME + timedelta(seconds=1),
            page=1,
            page_size=10,
        )
        saved = records[0]
        assert saved.credit_tier == CreditTier.C
        assert saved.district == District("München")
        assert saved.base_rate == Rate(Decimal("1.03"))
        assert saved.final_rate == Rate(Decimal("1.0815"))


class TestSqlAlchemyCalculationRecordRepositoryListByDateRange:
    async def test_returns_records_within_range(self, session: AsyncSession) -> None:
        repo = SqlAlchemyCalculationRecordRepository(session)
        inside = _make_record(calculated_at=_BASE_TIME)
        outside = _make_record(calculated_at=_BASE_TIME + timedelta(days=2))

        await repo.save(inside)
        await repo.save(outside)

        records, total = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(hours=1),
            to_dt=_BASE_TIME + timedelta(hours=1),
            page=1,
            page_size=10,
        )
        assert total == 1
        assert records[0].correlation_id == inside.correlation_id

    async def test_returns_correct_total_count(self, session: AsyncSession) -> None:
        repo = SqlAlchemyCalculationRecordRepository(session)
        for i in range(5):
            await repo.save(
                _make_record(calculated_at=_BASE_TIME + timedelta(minutes=i))
            )

        _, total = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(hours=1),
            to_dt=_BASE_TIME + timedelta(hours=1),
            page=1,
            page_size=2,
        )
        assert total == 5

    async def test_paginates_correctly(self, session: AsyncSession) -> None:
        repo = SqlAlchemyCalculationRecordRepository(session)
        for i in range(4):
            await repo.save(
                _make_record(calculated_at=_BASE_TIME + timedelta(minutes=i))
            )

        page1, _ = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(hours=1),
            to_dt=_BASE_TIME + timedelta(hours=1),
            page=1,
            page_size=2,
        )
        page2, _ = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(hours=1),
            to_dt=_BASE_TIME + timedelta(hours=1),
            page=2,
            page_size=2,
        )
        assert len(page1) == 2
        assert len(page2) == 2
        ids_page1 = {r.correlation_id for r in page1}
        ids_page2 = {r.correlation_id for r in page2}
        assert ids_page1.isdisjoint(ids_page2)

    async def test_orders_by_calculated_at_descending(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCalculationRecordRepository(session)
        earlier = _make_record(calculated_at=_BASE_TIME)
        later = _make_record(calculated_at=_BASE_TIME + timedelta(minutes=5))

        await repo.save(earlier)
        await repo.save(later)

        records, _ = await repo.list_by_date_range(
            from_dt=_BASE_TIME - timedelta(hours=1),
            to_dt=_BASE_TIME + timedelta(hours=1),
            page=1,
            page_size=10,
        )
        assert records[0].correlation_id == later.correlation_id
        assert records[1].correlation_id == earlier.correlation_id

    async def test_returns_empty_when_range_has_no_records(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCalculationRecordRepository(session)

        records, total = await repo.list_by_date_range(
            from_dt=datetime(2020, 1, 1, tzinfo=UTC),
            to_dt=datetime(2020, 1, 2, tzinfo=UTC),
            page=1,
            page_size=10,
        )
        assert records == []
        assert total == 0
