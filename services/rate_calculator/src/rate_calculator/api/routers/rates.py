from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from rate_calculator.api.dependencies import (
    get_credit_tier_config_repo,
    get_district_risk_config_repo,
    get_outbox_repo,
    get_postal_code_mapping_repo,
    get_system_rate_config_repo,
)
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
from rate_calculator.application.use_cases.commands.calculate_loan_rate import (
    CalculateLoanRateCommand,
    CalculateLoanRateUseCase,
)

router = APIRouter(prefix="/rates", tags=["rates"])


class CalculateRateRequest(BaseModel):
    postal_code: str
    loan_term_months: int
    credit_tier: str


class CalculateRateResponse(BaseModel):
    correlation_id: UUID
    final_rate: Decimal
    credit_tier: str
    district: str
    base_rate: Decimal
    term_multiplier: Decimal
    credit_tier_multiplier: Decimal
    regional_risk_multiplier: Decimal
    calculated_at: datetime


@router.post("/calculate", response_model=CalculateRateResponse, status_code=200)
async def calculate_rate(
    body: CalculateRateRequest,
    x_correlation_id: UUID = Header(),
    postal_code_mapping_repo: PostalCodeMappingRepository = Depends(
        get_postal_code_mapping_repo
    ),
    system_rate_config_repo: SystemRateConfigRepository = Depends(
        get_system_rate_config_repo
    ),
    credit_tier_config_repo: CreditTierConfigRepository = Depends(
        get_credit_tier_config_repo
    ),
    district_risk_config_repo: DistrictRiskConfigRepository = Depends(
        get_district_risk_config_repo
    ),
    outbox_repo: OutboxRepository = Depends(get_outbox_repo),
) -> CalculateRateResponse:
    use_case = CalculateLoanRateUseCase(
        postal_code_mapping_repo=postal_code_mapping_repo,
        system_rate_config_repo=system_rate_config_repo,
        credit_tier_config_repo=credit_tier_config_repo,
        district_risk_config_repo=district_risk_config_repo,
        outbox_repo=outbox_repo,
    )
    result = await use_case.execute(
        CalculateLoanRateCommand(
            correlation_id=x_correlation_id,
            postal_code=body.postal_code,
            loan_term_months=body.loan_term_months,
            credit_tier=body.credit_tier,
        )
    )
    return CalculateRateResponse(
        correlation_id=result.correlation_id,
        final_rate=result.final_rate,
        credit_tier=result.credit_tier,
        district=result.district,
        base_rate=result.base_rate,
        term_multiplier=result.term_multiplier,
        credit_tier_multiplier=result.credit_tier_multiplier,
        regional_risk_multiplier=result.regional_risk_multiplier,
        calculated_at=result.calculated_at,
    )
