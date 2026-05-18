from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rate_calculator.api.dependencies import (
    get_credit_tier_config_repo,
    get_district_risk_config_repo,
    get_outbox_repo,
    get_postal_code_mapping_repo,
    get_system_rate_config_repo,
)
from rate_calculator.api.error_handlers import (
    application_validation_handler,
    conflict_handler,
    domain_error_handler,
    not_found_handler,
)
from rate_calculator.api.routers import config as config_router
from rate_calculator.api.routers import rates as rates_router
from rate_calculator.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from rate_calculator.domain.exceptions import DomainError

from .fakes import (
    FakeCreditTierConfigRepository,
    FakeDistrictRiskConfigRepository,
    FakeOutboxRepository,
    FakePostalCodeMappingRepository,
    FakeSystemRateConfigRepository,
)


@pytest.fixture
def system_repo() -> FakeSystemRateConfigRepository:
    return FakeSystemRateConfigRepository()


@pytest.fixture
def credit_tier_repo() -> FakeCreditTierConfigRepository:
    return FakeCreditTierConfigRepository()


@pytest.fixture
def district_repo() -> FakeDistrictRiskConfigRepository:
    return FakeDistrictRiskConfigRepository()


@pytest.fixture
def postal_code_repo() -> FakePostalCodeMappingRepository:
    return FakePostalCodeMappingRepository()


@pytest.fixture
def outbox_repo() -> FakeOutboxRepository:
    return FakeOutboxRepository()


@pytest.fixture
def client(
    system_repo: FakeSystemRateConfigRepository,
    credit_tier_repo: FakeCreditTierConfigRepository,
    district_repo: FakeDistrictRiskConfigRepository,
    postal_code_repo: FakePostalCodeMappingRepository,
    outbox_repo: FakeOutboxRepository,
) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(rates_router.router, prefix="/api/v1")
    app.include_router(config_router.router, prefix="/api/v1")

    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]

    app.dependency_overrides[get_system_rate_config_repo] = lambda: system_repo
    app.dependency_overrides[get_credit_tier_config_repo] = lambda: credit_tier_repo
    app.dependency_overrides[get_district_risk_config_repo] = lambda: district_repo
    app.dependency_overrides[get_postal_code_mapping_repo] = lambda: postal_code_repo
    app.dependency_overrides[get_outbox_repo] = lambda: outbox_repo

    with TestClient(app) as c:
        yield c
