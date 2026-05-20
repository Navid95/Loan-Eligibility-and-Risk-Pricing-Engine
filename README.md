# Loan Eligibility and Risk Pricing Engine

A microservice system that calculates personalised annual loan rates for retail banking customers. Rates are derived from a configurable formula that combines a system-wide base rate with three multipliers: loan term, applicant credit tier, and a regional risk index based on where the applicant lives.

The system is designed around Domain-Driven Design principles and Onion Architecture. Two independently deployable services own distinct bounded contexts:

| Service | Bounded context | Role |
|---------|----------------|------|
| `rate_calculator` | Rate Calculation + Configuration & Risk Management | Resolves postal codes, applies the rate formula, manages all runtime configuration |
| `audit_log` | Audit & Compliance | Consumes calculation events asynchronously, persists an immutable record of every calculation |

All external traffic enters through **Kong Gateway**, which handles authentication, per-broker rate limiting, and correlation ID injection. Services communicate asynchronously via **RabbitMQ** using a transactional outbox pattern.

---

## Prerequisites

- Docker and Docker Compose
- [uv](https://github.com/astral-sh/uv) (for running tests locally)

---

## Running the stack

All commands run from the **repository root**.

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

This starts six containers:

| Container | Host port | Notes |
|-----------|-----------|-------|
| `rate-calculator` | 8001 | Direct access, no auth |
| `audit-log` | 8002 | Direct access, no auth |
| `kong` | 8000 (HTTP), 8444 (HTTPS) | Auth-enforcing gateway |
| `rate-calculator-db` | — | PostgreSQL, internal only |
| `audit-log-db` | — | PostgreSQL, internal only |
| `rabbitmq` | 15672 (management UI) | User: `nordvik` / `nordvik` |

Database migrations for both services run automatically on container startup.

---

## Seeding reference data (first run only)

On a fresh database the `rate_calculator` service starts but cannot calculate rates — reference data must be loaded once.

**With ADR-006 clustered risk multipliers (recommended):**

```bash
docker compose -f infra/docker-compose.yml run --rm \
  -v "$(pwd)/data/districts.csv:/tmp/districts.csv:ro" \
  -v "$(pwd)/data/district_risk_scores.csv:/tmp/district_risk_scores.csv:ro" \
  rate-calculator \
  uv run --package rate-calculator seed /tmp/districts.csv /tmp/district_risk_scores.csv
```

**With neutral multipliers (1.0 for all districts):**

```bash
docker compose -f infra/docker-compose.yml run --rm \
  -v "$(pwd)/data/districts.csv:/tmp/districts.csv:ro" \
  rate-calculator \
  uv run --package rate-calculator seed /tmp/districts.csv
```

Both commands seed:
- Base rate: `1.03`
- Credit tiers: `A=1.05`, `B=1.15`, `C=1.30`
- 383 district risk configs (multipliers from `district_risk_scores.csv`, or `1.0` if omitted)
- 8,231 postal code mappings from `districts.csv`

Re-running is safe — all operations are idempotent upserts.

The `audit_log` service requires no seeding.

---

## Service URLs

| Interface | URL | Auth |
|-----------|-----|------|
| `rate_calculator` Swagger UI | http://localhost:8001/docs | None (direct) |
| `audit_log` Swagger UI | http://localhost:8002/docs | None (direct) |
| Kong proxy (broker) | http://localhost:8000/api/v1/rates/calculate | API key — `apikey` header |
| Kong proxy (admin) | http://localhost:8000/api/v1/config/* | HTTP Basic Auth |
| Kong proxy (auditor) | http://localhost:8000/api/v1/records | HTTP Basic Auth |
| RabbitMQ management UI | http://localhost:15672 | `nordvik` / `nordvik` |

### Kong credentials

| Consumer | Group | Credential |
|----------|-------|------------|
| `broker-alice` | broker-group | `apikey: bkr-alice-a1b2c3d4e5f6` |
| `broker-bob` | broker-group | `apikey: bkr-bob-f6e5d4c3b2a1` |
| `admin-carol` | admin-group | `admin-carol:carol-adm-secret` |
| `admin-dave` | admin-group | `admin-dave:dave-adm-secret` |
| `auditor-alice` | auditor-group | `auditor-alice:alice-aud-secret` |

---

## Stopping the stack

```bash
docker compose -f infra/docker-compose.yml down -v --remove-orphans
```

`-v` removes all named volumes (database data, RabbitMQ state).

---

## Rate formula

```
Final Annual Rate (%) = Base Rate
                      × Multiplier(Loan Term)
                      × Multiplier(Credit Tier)
                      × Multiplier(Regional Risk Index)
```

| Loan term | Term multiplier |
|-----------|----------------|
| ≤ 12 months | 0.8 |
| 13–36 months | 1.0 |
| 37–60 months | 1.3 |
| > 60 months | 1.7 |

---

## Tests

Each service has five independent test layers. Run them from the **repository root**. Earlier layers are faster and require no external dependencies; run them first.

### rate_calculator

**Unit** — domain logic, value objects, use cases. No external dependencies.
```bash
uv run --package rate-calculator pytest services/rate_calculator/tests/unit -v
```

**Contract** — all FastAPI routes and error handlers via `TestClient` with in-memory fake repositories. No external dependencies.
```bash
uv run --package rate-calculator pytest services/rate_calculator/tests/contract -v
```

**Integration** — repository implementations against a real PostgreSQL database (spun up via testcontainers). Requires Docker.
```bash
uv run --package rate-calculator pytest services/rate_calculator/tests/integration -v
```

**Pact** — consumer-driven contract verifying that the `RateCalculated` event serialiser produces the exact shape `audit_log` expects. No external dependencies.
```bash
uv run --package rate-calculator pytest services/rate_calculator/tests/pact -v
```

**E2E** — full stack (Kong + service + RabbitMQ + PostgreSQL). Start the isolated E2E compose stack, seed reference data, then run tests:
```bash
docker compose -f infra/docker-compose.rc-e2e.yml up -d
docker compose -f infra/docker-compose.rc-e2e.yml run --rm \
  -v "$(pwd)/data/districts.csv:/tmp/districts.csv:ro" \
  rate-calculator \
  uv run --package rate-calculator seed /tmp/districts.csv
uv run --package rate-calculator pytest services/rate_calculator/tests/e2e -v
```

---

### audit_log

**Unit** — domain value objects, aggregate, use case validation, consumer ACK/NACK semantics. No external dependencies.
```bash
uv run --package audit-log pytest services/audit_log/tests/unit -v
```

**Contract** — `GET /api/v1/records` and all error handlers via `TestClient` with a fake repository. No external dependencies.
```bash
uv run --package audit-log pytest services/audit_log/tests/contract -v
```

**Integration** — `SqlAlchemyCalculationRecordRepository` against a real PostgreSQL database, including append-only enforcement (UPDATE and DELETE rejection verified at the DB level). Requires Docker.
```bash
uv run --package audit-log pytest services/audit_log/tests/integration -v
```

**Pact** — consumer side of the contract; defines the 9 fields expected in the `RateCalculated` event payload. No external dependencies.
```bash
uv run --package audit-log pytest services/audit_log/tests/pact -v
```

**E2E** — full async flow: publish event to RabbitMQ → consumer persists to DB → API returns record. Start the isolated E2E compose stack first:
```bash
docker compose -f infra/docker-compose.audit-e2e.yml up -d
uv run --package audit-log pytest services/audit_log/tests/e2e -v
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [ADR-001 — Service Boundaries](docs/adr/001-service-boundaries.md) | Why D1+D2 are co-located in `rate_calculator` and D3 is isolated in `audit_log`; rejection of the alternative boundary split |
| [ADR-002 — Database: rate_calculator](docs/adr/002-database-choice-rate-calculator.md) | Why PostgreSQL for the configuration and reference data store; rejected alternatives (MongoDB, Redis) |
| [ADR-003 — Database: audit_log](docs/adr/003-database-choice-audit-log.md) | Layered immutability model: statement-level UPDATE trigger + permission-level DELETE/TRUNCATE revoke; rejected alternatives |
| [ADR-004 — Message Broker](docs/adr/004-message-broker-choice.md) | Why RabbitMQ over Kafka; transactional outbox pattern; DLQ strategy |
| [ADR-005 — Security](docs/adr/005-security.md) | Kong Gateway DB-less mode; API key auth for brokers, Basic Auth for admins/auditors; GDPR data minimisation decisions |
| [ADR-006 — Regional Risk Index](docs/adr/006-regional-risk-index.md) | Geographic k-means clustering with East/West Germany economic anchoring as the initial risk seeding model |
| [ADR-007 — Testing Strategy](docs/adr/007-testing-strategy.md) | Five-layer test strategy per service: rationale, scope, and tooling for each layer |
| [ADR-008 — Observability](docs/adr/008-observability.md) | JSON structured logging to stdout; mandatory fields; log level policy; monitoring approach (documented, not implemented) |
| [Database Schemas](docs/database-schemas.md) | All tables, column types, constraints, indexes, and triggers for both services |
| [OpenAPI — rate_calculator](docs/openapi/rate_calculator.json) | Machine-readable OpenAPI 3.x spec for the rate calculation and configuration APIs |
| [OpenAPI — audit_log](docs/openapi/audit-log.json) | Machine-readable OpenAPI 3.x spec for the compliance records query API |
