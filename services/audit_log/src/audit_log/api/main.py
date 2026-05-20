import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from audit_log.infrastructure.logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

from audit_log.api.error_handlers import (  # noqa: E402
    application_validation_handler,
    domain_error_handler,
    not_found_handler,
)
from audit_log.api.routers import records  # noqa: E402
from audit_log.application.exceptions import (  # noqa: E402
    NotFoundError,
    ValidationError,
)
from audit_log.domain.exceptions import DomainError  # noqa: E402
from audit_log.infrastructure.config import get_settings  # noqa: E402
from audit_log.infrastructure.database.engine import (  # noqa: E402
    create_engine,
    create_session_factory,
)
from audit_log.infrastructure.messaging.consumer import AuditEventConsumer  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    engine = create_engine(settings.APP_DATABASE_URL)
    session_factory = create_session_factory(engine)
    app.state.session_factory = session_factory

    consumer = AuditEventConsumer(
        rabbitmq_url=settings.RABBITMQ_URL,
        queue_name=settings.RABBITMQ_QUEUE,
        session_factory=session_factory,
    )
    await consumer.start()

    yield

    await consumer.stop()
    await engine.dispose()


app = FastAPI(title="Audit Log", lifespan=lifespan)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    correlation_id = request.headers.get("X-Correlation-Id", "")
    try:
        response = await call_next(request)
    except Exception:
        logger.error(
            "%s %s — unhandled exception",
            request.method,
            request.url.path,
            exc_info=True,
            extra={"correlation_id": correlation_id},
        )
        raise
    status = response.status_code
    if status >= 500:
        logger.error(
            "%s %s → %d",
            request.method,
            request.url.path,
            status,
            extra={"correlation_id": correlation_id},
        )
    elif status >= 400:
        logger.warning(
            "%s %s → %d",
            request.method,
            request.url.path,
            status,
            extra={"correlation_id": correlation_id},
        )
    return response


app.include_router(records.router, prefix="/api/v1")

app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
