# Build context must be monorepo root:
#   docker build -f services/rate_calculator/Dockerfile .
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY services/rate_calculator/pyproject.toml ./services/rate_calculator/pyproject.toml
COPY services/rate_calculator/src ./services/rate_calculator/src
COPY services/rate_calculator/migrations ./services/rate_calculator/migrations
COPY services/rate_calculator/alembic.ini ./services/rate_calculator/alembic.ini

RUN uv sync --frozen --no-dev --package rate-calculator


FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/
COPY --from=builder /app /app

WORKDIR /app

EXPOSE 8000

CMD ["uv", "run", "--package", "rate-calculator", \
     "sh", "-c", \
     "alembic -c services/rate_calculator/alembic.ini upgrade head && \
      uvicorn rate_calculator.api.main:app --host 0.0.0.0 --port 8000"]
