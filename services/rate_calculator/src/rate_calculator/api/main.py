import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from rate_calculator.infrastructure.logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

from rate_calculator.api.error_handlers import (  # noqa: E402
    application_validation_handler,
    conflict_handler,
    domain_error_handler,
    not_found_handler,
)
from rate_calculator.api.routers import config, rates  # noqa: E402
from rate_calculator.application.exceptions import (  # noqa: E402
    ConflictError,
    NotFoundError,
    ValidationError,
)
from rate_calculator.domain.exceptions import DomainError  # noqa: E402
from rate_calculator.infrastructure.config import get_settings  # noqa: E402
from rate_calculator.infrastructure.database.engine import (  # noqa: E402
    create_engine,
    create_session_factory,
)
from rate_calculator.infrastructure.messaging.rabbitmq_publisher import (  # noqa: E402
    RabbitMQPublisher,
)
from rate_calculator.infrastructure.outbox.relay import OutboxRelay  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)
    app.state.session_factory = session_factory

    publisher = RabbitMQPublisher(
        rabbitmq_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
    )
    await publisher.connect()
    app.state.publisher = publisher

    relay = OutboxRelay(
        session_factory=session_factory,
        publisher=publisher,
        interval_seconds=settings.OUTBOX_RELAY_INTERVAL_SECONDS,
    )
    relay.start()
    app.state.relay = relay

    yield

    relay.stop()
    await publisher.close()
    await engine.dispose()


app = FastAPI(title="Rate Calculator", lifespan=lifespan)


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


app.include_router(rates.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")

app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
