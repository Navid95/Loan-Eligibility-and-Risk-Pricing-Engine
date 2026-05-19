from fastapi import Request
from fastapi.responses import JSONResponse

from audit_log.application.exceptions import NotFoundError, ValidationError
from audit_log.domain.exceptions import DomainError


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "context": exc.context},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.reason})


async def application_validation_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.reason})
