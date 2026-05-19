from datetime import datetime
from uuid import UUID

from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate


class CalculationRecord:
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
        final_rate: Rate,
        calculated_at: datetime,
        recorded_at: datetime,
    ) -> None:
        self._correlation_id = correlation_id
        self._credit_tier = credit_tier
        self._district = district
        self._base_rate = base_rate
        self._term_multiplier = term_multiplier
        self._credit_tier_multiplier = credit_tier_multiplier
        self._regional_risk_multiplier = regional_risk_multiplier
        self._final_rate = final_rate
        self._calculated_at = calculated_at
        self._recorded_at = recorded_at

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
    def final_rate(self) -> Rate:
        return self._final_rate

    @property
    def calculated_at(self) -> datetime:
        return self._calculated_at

    @property
    def recorded_at(self) -> datetime:
        return self._recorded_at
