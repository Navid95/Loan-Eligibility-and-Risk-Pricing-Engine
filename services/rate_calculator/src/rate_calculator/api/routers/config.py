from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from rate_calculator.api.dependencies import (
    get_credit_tier_config_repo,
    get_district_risk_config_repo,
    get_system_rate_config_repo,
)
from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.application.use_cases.commands.bulk_update_region_risk_index import (  # noqa: E501
    BulkUpdateRegionRiskIndexCommand,
    BulkUpdateRegionRiskIndexUseCase,
)
from rate_calculator.application.use_cases.commands.create_credit_tier_config import (
    CreateCreditTierConfigCommand,
    CreateCreditTierConfigUseCase,
)
from rate_calculator.application.use_cases.commands.update_base_rate import (
    UpdateBaseRateCommand,
    UpdateBaseRateUseCase,
)
from rate_calculator.application.use_cases.commands.update_credit_tier_multiplier import (  # noqa: E501
    UpdateCreditTierMultiplierCommand,
    UpdateCreditTierMultiplierUseCase,
)
from rate_calculator.application.use_cases.commands.update_district_risk_index import (
    UpdateDistrictRiskIndexCommand,
    UpdateDistrictRiskIndexUseCase,
)
from rate_calculator.application.use_cases.get_district_risk_config import (
    GetDistrictRiskConfigQuery,
    GetDistrictRiskConfigUseCase,
)
from rate_calculator.application.use_cases.get_system_config import (
    GetSystemConfigUseCase,
)
from rate_calculator.application.use_cases.list_credit_tier_configs import (
    ListCreditTierConfigsUseCase,
)
from rate_calculator.application.use_cases.list_district_risk_configs import (
    ListDistrictRiskConfigsQuery,
    ListDistrictRiskConfigsUseCase,
)

router = APIRouter(prefix="/config", tags=["config"])


# --- Pydantic schemas ---


class SystemConfigResponse(BaseModel):
    base_rate: Decimal


class UpdateBaseRateRequest(BaseModel):
    base_rate: Decimal


class CreditTierConfigResponse(BaseModel):
    tier: str
    multiplier: Decimal


class CreateCreditTierConfigRequest(BaseModel):
    tier: str
    multiplier: Decimal


class UpdateMultiplierRequest(BaseModel):
    multiplier: Decimal


class DistrictRiskConfigResponse(BaseModel):
    district: str
    multiplier: Decimal


class PagedDistrictRiskConfigsResponse(BaseModel):
    items: list[DistrictRiskConfigResponse]
    total: int
    page: int
    page_size: int


class BulkUpdateResponse(BaseModel):
    updated: int


# --- System config endpoints ---


@router.get("/system", response_model=SystemConfigResponse)
async def get_system_config(
    repo: SystemRateConfigRepository = Depends(get_system_rate_config_repo),
) -> SystemConfigResponse:
    result = await GetSystemConfigUseCase(system_rate_config_repo=repo).execute()
    return SystemConfigResponse(base_rate=result.base_rate)


@router.put("/system", response_model=SystemConfigResponse)
async def update_base_rate(
    body: UpdateBaseRateRequest,
    repo: SystemRateConfigRepository = Depends(get_system_rate_config_repo),
) -> SystemConfigResponse:
    await UpdateBaseRateUseCase(system_rate_config_repo=repo).execute(
        UpdateBaseRateCommand(new_rate=body.base_rate)
    )
    result = await GetSystemConfigUseCase(system_rate_config_repo=repo).execute()
    return SystemConfigResponse(base_rate=result.base_rate)


# --- Credit tier config endpoints ---


@router.get("/credit-tiers", response_model=list[CreditTierConfigResponse])
async def list_credit_tier_configs(
    repo: CreditTierConfigRepository = Depends(get_credit_tier_config_repo),
) -> list[CreditTierConfigResponse]:
    results = await ListCreditTierConfigsUseCase(credit_tier_config_repo=repo).execute()
    return [
        CreditTierConfigResponse(tier=r.tier, multiplier=r.multiplier) for r in results
    ]


@router.post("/credit-tiers", response_model=CreditTierConfigResponse, status_code=201)
async def create_credit_tier_config(
    body: CreateCreditTierConfigRequest,
    repo: CreditTierConfigRepository = Depends(get_credit_tier_config_repo),
) -> CreditTierConfigResponse:
    await CreateCreditTierConfigUseCase(credit_tier_config_repo=repo).execute(
        CreateCreditTierConfigCommand(tier=body.tier, multiplier=body.multiplier)
    )
    return CreditTierConfigResponse(tier=body.tier, multiplier=body.multiplier)


@router.put("/credit-tiers/{tier}", response_model=CreditTierConfigResponse)
async def update_credit_tier_multiplier(
    tier: str,
    body: UpdateMultiplierRequest,
    repo: CreditTierConfigRepository = Depends(get_credit_tier_config_repo),
) -> CreditTierConfigResponse:
    await UpdateCreditTierMultiplierUseCase(credit_tier_config_repo=repo).execute(
        UpdateCreditTierMultiplierCommand(tier=tier, new_multiplier=body.multiplier)
    )
    return CreditTierConfigResponse(tier=tier, multiplier=body.multiplier)


# --- District risk config endpoints ---


@router.get("/districts", response_model=PagedDistrictRiskConfigsResponse)
async def list_district_risk_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    repo: DistrictRiskConfigRepository = Depends(get_district_risk_config_repo),
) -> PagedDistrictRiskConfigsResponse:
    result = await ListDistrictRiskConfigsUseCase(
        district_risk_config_repo=repo
    ).execute(ListDistrictRiskConfigsQuery(page=page, page_size=page_size))
    return PagedDistrictRiskConfigsResponse(
        items=[
            DistrictRiskConfigResponse(district=i.district, multiplier=i.multiplier)
            for i in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/districts/{district}", response_model=DistrictRiskConfigResponse)
async def get_district_risk_config(
    district: str,
    repo: DistrictRiskConfigRepository = Depends(get_district_risk_config_repo),
) -> DistrictRiskConfigResponse:
    result = await GetDistrictRiskConfigUseCase(district_risk_config_repo=repo).execute(
        GetDistrictRiskConfigQuery(district=district)
    )
    return DistrictRiskConfigResponse(
        district=result.district, multiplier=result.multiplier
    )


@router.put("/districts/{district}", response_model=DistrictRiskConfigResponse)
async def update_district_risk_index(
    district: str,
    body: UpdateMultiplierRequest,
    repo: DistrictRiskConfigRepository = Depends(get_district_risk_config_repo),
) -> DistrictRiskConfigResponse:
    await UpdateDistrictRiskIndexUseCase(district_risk_config_repo=repo).execute(
        UpdateDistrictRiskIndexCommand(
            district=district, new_multiplier=body.multiplier
        )
    )
    return DistrictRiskConfigResponse(district=district, multiplier=body.multiplier)


@router.put("/regions/{region2}", response_model=BulkUpdateResponse)
async def bulk_update_region_risk_index(
    region2: str,
    body: UpdateMultiplierRequest,
    repo: DistrictRiskConfigRepository = Depends(get_district_risk_config_repo),
) -> BulkUpdateResponse:
    updated = await BulkUpdateRegionRiskIndexUseCase(
        district_risk_config_repo=repo
    ).execute(
        BulkUpdateRegionRiskIndexCommand(
            region2=region2, new_multiplier=body.multiplier
        )
    )
    return BulkUpdateResponse(updated=updated)
