from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from rate_calculator.application.exceptions import NotFoundError, ValidationError
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.ports.outbox_repository import OutboxRepository
from rate_calculator.application.ports.postal_code_mapping_repository import (
    PostalCodeMappingRepository,
)
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.domain.aggregates import CalculationRequest
from rate_calculator.domain.value_objects import (
    CreditTier,
    LoanTerm,
    Multiplier,
    PostalCode,
)


@dataclass(frozen=True)
class CalculateLoanRateCommand:
    correlation_id: UUID
    postal_code: str
    loan_term_months: int
    credit_tier: str


@dataclass(frozen=True)
class CalculateLoanRateResult:
    correlation_id: UUID
    final_rate: Decimal
    credit_tier: str
    district: str
    base_rate: Decimal
    term_multiplier: Decimal
    credit_tier_multiplier: Decimal
    regional_risk_multiplier: Decimal
    calculated_at: datetime


class CalculateLoanRateUseCase:
    def __init__(
        self,
        *,
        postal_code_mapping_repo: PostalCodeMappingRepository,
        system_rate_config_repo: SystemRateConfigRepository,
        credit_tier_config_repo: CreditTierConfigRepository,
        district_risk_config_repo: DistrictRiskConfigRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._postal_code_mapping_repo = postal_code_mapping_repo
        self._system_rate_config_repo = system_rate_config_repo
        self._credit_tier_config_repo = credit_tier_config_repo
        self._district_risk_config_repo = district_risk_config_repo
        self._outbox_repo = outbox_repo

    async def execute(
        self, command: CalculateLoanRateCommand
    ) -> CalculateLoanRateResult:
        postal_code = PostalCode(command.postal_code)
        loan_term = LoanTerm(command.loan_term_months)

        try:
            credit_tier = CreditTier(command.credit_tier)
        except ValueError:
            raise ValidationError(
                reason=f"'{command.credit_tier}' is not a valid credit tier"
            )

        mapping = await self._postal_code_mapping_repo.get(postal_code)
        if mapping is None:
            raise NotFoundError(reason=f"postal code '{command.postal_code}' not found")

        district = mapping.district

        system_config = await self._system_rate_config_repo.get()

        tier_config = await self._credit_tier_config_repo.get(credit_tier)
        if tier_config is None:
            raise NotFoundError(
                reason=f"credit tier config for '{credit_tier.value}' not found"
            )

        district_config = await self._district_risk_config_repo.get(district)
        if district_config is None:
            raise NotFoundError(
                reason=f"district risk config for '{district.name}' not found"
            )

        term_mult_value = loan_term.term_multiplier()
        calc_request = CalculationRequest(
            correlation_id=command.correlation_id,
            credit_tier=credit_tier,
            district=district,
            base_rate=system_config.base_rate,
            term_multiplier=Multiplier(term_mult_value),
            credit_tier_multiplier=tier_config.multiplier,
            regional_risk_multiplier=district_config.multiplier,
        )

        final_rate = calc_request.calculate()

        for event in calc_request.pull_events():
            await self._outbox_repo.save(event)

        assert calc_request.calculated_at is not None
        return CalculateLoanRateResult(
            correlation_id=command.correlation_id,
            final_rate=final_rate.value,
            credit_tier=credit_tier.value,
            district=district.name,
            base_rate=system_config.base_rate.value,
            term_multiplier=term_mult_value,
            credit_tier_multiplier=tier_config.multiplier.value,
            regional_risk_multiplier=district_config.multiplier.value,
            calculated_at=calc_request.calculated_at,
        )
