from fastapi import Request
from fastapi.responses import JSONResponse

from rate_calculator.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from rate_calculator.domain.exceptions import DomainError


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "context": exc.context},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.reason})


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.reason})


async def application_validation_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.reason})
