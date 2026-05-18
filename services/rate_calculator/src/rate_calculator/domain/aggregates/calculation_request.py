from datetime import UTC, datetime
from uuid import UUID

from rate_calculator.domain.events.rate_calculated import RateCalculated
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import CreditTier, District, Multiplier, Rate


class CalculationRequest:
    def __init__(
        self,
        *,
        correlation_id: UUID,
        credit_tier: CreditTier,
        district: District,
        base_rate: Rate,
        term_multiplier: Multiplier,
        credit_tier_multiplier: Multiplier,
        regional_risk_multiplier: Multiplier,
    ) -> None:
        self._correlation_id = correlation_id
        self._credit_tier = credit_tier
        self._district = district
        self._base_rate = base_rate
        self._term_multiplier = term_multiplier
        self._credit_tier_multiplier = credit_tier_multiplier
        self._regional_risk_multiplier = regional_risk_multiplier
        self._final_rate: Rate | None = None
        self._calculated_at: datetime | None = None
        self._events: list[RateCalculated] = []

    @property
    def correlation_id(self) -> UUID:
        return self._correlation_id

    @property
    def credit_tier(self) -> CreditTier:
        return self._credit_tier

    @property
    def district(self) -> District:
        return self._district

    @property
    def base_rate(self) -> Rate:
        return self._base_rate

    @property
    def term_multiplier(self) -> Multiplier:
        return self._term_multiplier

    @property
    def credit_tier_multiplier(self) -> Multiplier:
        return self._credit_tier_multiplier

    @property
    def regional_risk_multiplier(self) -> Multiplier:
        return self._regional_risk_multiplier

    @property
    def final_rate(self) -> Rate | None:
        return self._final_rate

    @property
    def calculated_at(self) -> datetime | None:
        return self._calculated_at

    def calculate(self) -> Rate:
        if self._final_rate is not None:
            raise DomainError(
                context={"reason": "calculation has already been performed"}
            )

        final_value = (
            self._base_rate.value
            * self._term_multiplier.value
            * self._credit_tier_multiplier.value
            * self._regional_risk_multiplier.value
        )
        self._final_rate = Rate(final_value)
        self._calculated_at = datetime.now(UTC)

        event = RateCalculated(
            correlation_id=self._correlation_id,
            credit_tier=self._credit_tier,
            district=self._district,
            base_rate=self._base_rate,
            term_multiplier=self._term_multiplier,
            credit_tier_multiplier=self._credit_tier_multiplier,
            regional_risk_multiplier=self._regional_risk_multiplier,
            final_rate=self._final_rate,
            calculated_at=self._calculated_at,
        )
        if not any(e.correlation_id == event.correlation_id for e in self._events):
            self._events.append(event)

        return self._final_rate

    def pull_events(self) -> list[RateCalculated]:
        events = list(self._events)
        self._events.clear()
        return events
