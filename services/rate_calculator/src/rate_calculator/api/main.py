from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from rate_calculator.api.error_handlers import (
    application_validation_handler,
    conflict_handler,
    domain_error_handler,
    not_found_handler,
)
from rate_calculator.api.routers import config, rates
from rate_calculator.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.infrastructure.config import get_settings
from rate_calculator.infrastructure.database.engine import (
    create_engine,
    create_session_factory,
)
from rate_calculator.infrastructure.messaging.rabbitmq_publisher import (
    RabbitMQPublisher,
)
from rate_calculator.infrastructure.outbox.relay import OutboxRelay


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

app.include_router(rates.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")

app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
