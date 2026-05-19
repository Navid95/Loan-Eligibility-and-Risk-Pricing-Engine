from collections.abc import Generator

import pytest
from audit_log.api.dependencies import get_calculation_record_repo
from audit_log.api.error_handlers import (
    application_validation_handler,
    domain_error_handler,
    not_found_handler,
)
from audit_log.api.routers import records as records_router
from audit_log.application.exceptions import NotFoundError, ValidationError
from audit_log.domain.exceptions import DomainError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .fakes import FakeCalculationRecordRepository


@pytest.fixture
def repo() -> FakeCalculationRecordRepository:
    return FakeCalculationRecordRepository()


@pytest.fixture
def client(
    repo: FakeCalculationRecordRepository,
) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(records_router.router, prefix="/api/v1")

    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]

    app.dependency_overrides[get_calculation_record_repo] = lambda: repo

    with TestClient(app) as c:
        yield c
