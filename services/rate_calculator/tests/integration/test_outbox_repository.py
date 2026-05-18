from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from rate_calculator.domain.events.rate_calculated import RateCalculated
from rate_calculator.domain.value_objects.credit_tier import CreditTier
from rate_calculator.domain.value_objects.district import District
from rate_calculator.domain.value_objects.multiplier import Multiplier
from rate_calculator.domain.value_objects.rate import Rate
from rate_calculator.infrastructure.database.models import OutboxModel
from rate_calculator.infrastructure.repositories.outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def _make_event(correlation_id=None) -> RateCalculated:
    return RateCalculated(
        correlation_id=correlation_id or uuid4(),
        credit_tier=CreditTier.A,
        district=District("München"),
        base_rate=Rate(Decimal("5.0")),
        term_multiplier=Multiplier(Decimal("1.0")),
        credit_tier_multiplier=Multiplier(Decimal("1.2")),
        regional_risk_multiplier=Multiplier(Decimal("1.1")),
        final_rate=Rate(Decimal("6.6")),
        calculated_at=datetime.now(UTC),
    )


class TestSqlAlchemyOutboxRepository:
    async def test_save_persists_row(self, session: AsyncSession) -> None:
        event = _make_event()
        repo = SqlAlchemyOutboxRepository(session)

        await repo.save(event)

        result = await session.execute(
            select(OutboxModel).where(
                OutboxModel.correlation_id == event.correlation_id
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.correlation_id == event.correlation_id

    async def test_payload_has_all_keys(self, session: AsyncSession) -> None:
        event = _make_event()
        repo = SqlAlchemyOutboxRepository(session)
        await repo.save(event)

        result = await session.execute(
            select(OutboxModel).where(
                OutboxModel.correlation_id == event.correlation_id
            )
        )
        row = result.scalar_one()
        expected_keys = {
            "correlation_id",
            "credit_tier",
            "district",
            "base_rate",
            "term_multiplier",
            "credit_tier_multiplier",
            "regional_risk_multiplier",
            "final_rate",
            "calculated_at",
        }
        assert set(row.payload.keys()) == expected_keys

    async def test_duplicate_correlation_id_raises_integrity_error(
        self, session: AsyncSession
    ) -> None:
        correlation_id = uuid4()
        repo = SqlAlchemyOutboxRepository(session)

        await repo.save(_make_event(correlation_id))
        with pytest.raises(IntegrityError):
            await repo.save(_make_event(correlation_id))
