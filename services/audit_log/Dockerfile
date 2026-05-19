# Build context must be monorepo root:
#   docker build -f services/audit_log/Dockerfile .
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY services/audit_log/pyproject.toml ./services/audit_log/pyproject.toml
COPY services/audit_log/src ./services/audit_log/src

RUN uv sync --frozen --no-dev --package audit-log


FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/
COPY --from=builder /app /app

WORKDIR /app

COPY services/audit_log/migrations ./services/audit_log/migrations
COPY services/audit_log/alembic.ini ./services/audit_log/alembic.ini

EXPOSE 8000

CMD uv run --package audit-log sh -c \
    "alembic -c services/audit_log/alembic.ini upgrade head && \
     uvicorn audit_log.api.main:app --host 0.0.0.0 --port 8000"
