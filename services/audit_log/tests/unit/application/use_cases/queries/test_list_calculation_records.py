from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from audit_log.application.exceptions import ValidationError
from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)
from audit_log.application.use_cases.queries.list_calculation_records import (
    ListCalculationRecordsQuery,
    ListCalculationRecordsUseCase,
)
from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate

_FROM = datetime(2026, 1, 1, tzinfo=UTC)
_TO = datetime(2026, 12, 31, tzinfo=UTC)


def _make_record() -> CalculationRecord:
    return CalculationRecord(
        correlation_id=uuid4(),
        credit_tier=CreditTier.A,
        district=District("München"),
        base_rate=Rate(Decimal("1.03")),
        term_multiplier=Multiplier(Decimal("1.0")),
        credit_tier_multiplier=Multiplier(Decimal("1.05")),
        regional_risk_multiplier=Multiplier(Decimal("1.0")),
        final_rate=Rate(Decimal("1.0815")),
        calculated_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 5, 19, 10, 0, 1, tzinfo=UTC),
    )


@pytest.fixture
def repo() -> AsyncMock:
    mock = AsyncMock(spec=CalculationRecordRepository)
    mock.list_by_date_range.return_value = ([], 0)
    return mock


@pytest.fixture
def use_case(repo: AsyncMock) -> ListCalculationRecordsUseCase:
    return ListCalculationRecordsUseCase(repo=repo)


class TestListCalculationRecordsUseCase:
    async def test_returns_empty_result_when_no_records(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        result = await use_case.execute(
            ListCalculationRecordsQuery(from_dt=_FROM, to_dt=_TO, page=1, page_size=50)
        )
        assert result.items == []
        assert result.total == 0

    async def test_result_carries_pagination_metadata(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        result = await use_case.execute(
            ListCalculationRecordsQuery(from_dt=_FROM, to_dt=_TO, page=3, page_size=25)
        )
        assert result.page == 3
        assert result.page_size == 25

    async def test_maps_domain_record_to_result_item(
        self, use_case: ListCalculationRecordsUseCase, repo: AsyncMock
    ) -> None:
        record = _make_record()
        repo.list_by_date_range.return_value = ([record], 1)

        result = await use_case.execute(
            ListCalculationRecordsQuery(from_dt=_FROM, to_dt=_TO, page=1, page_size=50)
        )

        assert result.total == 1
        item = result.items[0]
        assert item.correlation_id == record.correlation_id
        assert item.credit_tier == "A"
        assert item.district == "München"
        assert item.base_rate == Decimal("1.03")
        assert item.final_rate == Decimal("1.0815")

    async def test_passes_query_params_to_repo(
        self, use_case: ListCalculationRecordsUseCase, repo: AsyncMock
    ) -> None:
        await use_case.execute(
            ListCalculationRecordsQuery(from_dt=_FROM, to_dt=_TO, page=2, page_size=10)
        )
        repo.list_by_date_range.assert_awaited_once_with(
            from_dt=_FROM, to_dt=_TO, page=2, page_size=10
        )

    async def test_raises_validation_error_when_from_equals_to(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                ListCalculationRecordsQuery(
                    from_dt=_FROM, to_dt=_FROM, page=1, page_size=50
                )
            )

    async def test_raises_validation_error_when_from_after_to(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                ListCalculationRecordsQuery(
                    from_dt=_TO, to_dt=_FROM, page=1, page_size=50
                )
            )

    @pytest.mark.parametrize("page", [0, -1])
    async def test_raises_validation_error_when_page_less_than_1(
        self, use_case: ListCalculationRecordsUseCase, page: int
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                ListCalculationRecordsQuery(
                    from_dt=_FROM, to_dt=_TO, page=page, page_size=50
                )
            )

    @pytest.mark.parametrize("page_size", [0, -1])
    async def test_raises_validation_error_when_page_size_below_minimum(
        self, use_case: ListCalculationRecordsUseCase, page_size: int
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                ListCalculationRecordsQuery(
                    from_dt=_FROM, to_dt=_TO, page=1, page_size=page_size
                )
            )

    async def test_raises_validation_error_when_page_size_exceeds_maximum(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        with pytest.raises(ValidationError):
            await use_case.execute(
                ListCalculationRecordsQuery(
                    from_dt=_FROM, to_dt=_TO, page=1, page_size=101
                )
            )

    async def test_page_size_100_is_accepted(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        result = await use_case.execute(
            ListCalculationRecordsQuery(from_dt=_FROM, to_dt=_TO, page=1, page_size=100)
        )
        assert result.page_size == 100

    async def test_to_just_after_from_is_valid(
        self, use_case: ListCalculationRecordsUseCase
    ) -> None:
        result = await use_case.execute(
            ListCalculationRecordsQuery(
                from_dt=_FROM,
                to_dt=_FROM + timedelta(seconds=1),
                page=1,
                page_size=50,
            )
        )
        assert result.total == 0
