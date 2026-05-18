from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.application.ports.outbox_repository import OutboxRepository
from rate_calculator.domain.events.rate_calculated import RateCalculated
from rate_calculator.infrastructure.database.models import OutboxModel


def _serialise(event: RateCalculated) -> dict[str, str]:
    return {
        "correlation_id": str(event.correlation_id),
        "credit_tier": event.credit_tier.value,
        "district": event.district.name,
        "base_rate": str(event.base_rate.value),
        "term_multiplier": str(event.term_multiplier.value),
        "credit_tier_multiplier": str(event.credit_tier_multiplier.value),
        "regional_risk_multiplier": str(event.regional_risk_multiplier.value),
        "final_rate": str(event.final_rate.value),
        "calculated_at": event.calculated_at.isoformat(),
    }


class SqlAlchemyOutboxRepository(OutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: RateCalculated) -> None:
        row = OutboxModel(
            correlation_id=event.correlation_id,
            payload=_serialise(event),
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
