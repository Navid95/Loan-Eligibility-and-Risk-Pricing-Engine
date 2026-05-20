from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from audit_log.api.error_handlers import (
    application_validation_handler,
    domain_error_handler,
    not_found_handler,
)
from audit_log.api.routers import records
from audit_log.application.exceptions import NotFoundError, ValidationError
from audit_log.domain.exceptions import DomainError
from audit_log.infrastructure.config import get_settings
from audit_log.infrastructure.database.engine import (
    create_engine,
    create_session_factory,
)
from audit_log.infrastructure.messaging.consumer import AuditEventConsumer


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

app.include_router(records.router, prefix="/api/v1")

app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, application_validation_handler)  # type: ignore[arg-type]


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
