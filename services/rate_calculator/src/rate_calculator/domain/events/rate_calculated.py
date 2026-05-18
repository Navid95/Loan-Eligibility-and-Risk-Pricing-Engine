from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rate_calculator.domain.value_objects import CreditTier, District, Multiplier, Rate


@dataclass(frozen=True)
class RateCalculated:
    correlation_id: UUID
    credit_tier: CreditTier
    district: District
    base_rate: Rate
    term_multiplier: Multiplier
    credit_tier_multiplier: Multiplier
    regional_risk_multiplier: Multiplier
    final_rate: Rate
    calculated_at: datetime
