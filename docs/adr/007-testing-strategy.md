# ADR-007: Testing Strategy

**Status:** Accepted

---

## Context

The system consists of two services (`rate_calculator` and `audit_log`) communicating asynchronously via a message broker. Both services follow Onion Architecture with strict inward dependencies and are designed using DDD principles.

Several properties of the system create specific testing requirements:

- The domain layer is decoupled from infrastructure by design — domain logic is testable in isolation.
- Each service defines ports (abstract interfaces) and adapters (concrete implementations). The Onion constraint is only valuable if adapters are verified to honour their port contracts.
- The `audit_log` service enforces append-only immutability at the database permission level — this constraint cannot be verified without a real database.
- The two services share an async message contract: `rate_calculator` publishes an audit event and `audit_log` consumes it. A breaking change to the message shape must be caught before it reaches a shared environment.
- Financial calculations and compliance audit records require high confidence — test coverage must reach infrastructure and integration boundaries, not just domain logic.

---

## Decision

Each service has a complete, independent test suite with five layers. Test layers are ordered from fastest/most isolated to slowest/most integrated.

### Layer 1 — Unit Tests

Scope: pure domain logic with no I/O or framework dependencies.

**`rate_calculator`:**
- Rate formula application (base rate × term multiplier × credit tier multiplier × regional risk multiplier)
- Loan term band resolution (≤12, 13–36, 37–60, >60 months)
- Credit tier multiplier lookup
- Postcode → REGION3 → risk index resolution

**`audit_log`:**
- Domain value objects and aggregate construction and field validation
- `ListCalculationRecordsUseCase` validation and DTO mapping
- RabbitMQ consumer deserialization and ACK/NACK semantics

Tooling: pytest, AsyncMock. Repository interfaces are replaced with `AsyncMock(spec=<Port>)` in use case tests — no database, no network.

### Layer 2 — Contract Tests

Scope: all FastAPI routes and error handlers tested via `TestClient` with in-memory fake repositories — no database, no network.

Fake implementations replace all repository ports with in-memory stores. The real routers, dependency injection wiring, and error handlers are exercised against these fakes. This layer verifies the full HTTP contract of each service: request validation, response shape, status codes, and error handling.

**`rate_calculator`:** all rates and config endpoints; `FakeOutboxRepository` exposes a `.saved` list to assert that `RateCalculated` events are written on successful calculation.

**`audit_log`:** `GET /api/v1/records` and all error handlers; `FakeCalculationRecordRepository` supports seeding, idempotency, filtering, sorting, and pagination.

Tooling: pytest, FastAPI `TestClient`, fake repository implementations. No external dependencies required.

### Layer 3 — Integration Tests

Scope: repository implementations tested against a real PostgreSQL database.

Real databases are used via `testcontainers-python`. Mocking the database is explicitly rejected: the `audit_log` service's append-only enforcement (INSERT-only database user with UPDATE and DELETE revoked, plus a BEFORE UPDATE trigger) is a database-level constraint that cannot be verified without a real database. Consistency between test and production behaviour is not achievable with mocked repositories.

**`rate_calculator`:** PostgreSQL repository implementations — config reads/writes, postcode lookup, outbox persistence.

**`audit_log`:** `SqlAlchemyCalculationRecordRepository` — save and retrieval, idempotency on duplicate `correlation_id`, date range filtering, pagination, `calculated_at DESC` ordering, and append-only enforcement (UPDATE and DELETE must be rejected at the database level).

Tooling: pytest, `testcontainers-python`. Requires Docker. No other services needed.

### Layer 4 — Consumer-Driven Contract Tests (Pact)

Scope: the async message contract between `rate_calculator` (producer) and `audit_log` (consumer).

`audit_log` defines the Pact consumer contract — the 9 message fields and types it requires from the audit event (`correlation_id`, `credit_tier`, `district`, `base_rate`, `term_multiplier`, `credit_tier_multiplier`, `regional_risk_multiplier`, `final_rate`, `calculated_at`). `rate_calculator` verifies that its serialiser produces exactly that shape.

Pact files are written to `/tmp/pacts/` (the pact-python Ruby binary cannot handle paths with spaces). This layer requires no external dependencies — no running services, no Pact broker.

This layer protects against breaking changes to the shared event schema without requiring a full integration environment.

Tooling: `pact-python` v2.3+. No external dependencies required.

### Layer 5 — End-to-End Tests

Scope: full system behaviour verified against a live Docker Compose stack.

Each service has its own isolated E2E compose file:
- `rate_calculator`: `infra/docker-compose.rc-e2e.yml` (rate-calculator + Kong + RabbitMQ + PostgreSQL; no audit-log)
- `audit_log`: `infra/docker-compose.audit-e2e.yml` (audit-log + Kong + RabbitMQ + PostgreSQL; no rate-calculator)

The E2E suite is intentionally narrow — happy path and a small number of critical edge cases only. Speed and reliability are prioritised over breadth; layers 1–4 provide the breadth.

**`rate_calculator` E2E covers:** authentication enforcement (valid/invalid keys, cross-auth rejections), rate calculation with full breakdown fields and all four term brackets, RabbitMQ publication verified via the management API, config management reflected in subsequent calculations.

**`audit_log` E2E covers:** validation enforcement, full async publish→persist→query round trip, field preservation, idempotency on duplicate `correlation_id`, pagination metadata.

Tooling: pytest, httpx, live Docker Compose stack. No external dependencies beyond Docker.

---

## Consequences

**Positive:**
- Domain logic is tested in complete isolation — fast feedback, no infrastructure required for the innermost layers.
- API contracts (routes, error handlers, response shapes) are verified without infrastructure using fake repositories — fast and deterministic.
- Append-only immutability is verified at the database level, matching the production enforcement mechanism.
- Cross-service contract breakage is caught before it reaches a shared environment, without requiring both services to be running simultaneously.
- Each service is independently testable — no shared test infrastructure between services.

**Negative / trade-offs:**
- Five test layers per service increases the test surface to maintain. This cost is justified by the financial and compliance nature of the domain.
- Testcontainers adds latency to integration test runs. Acceptable given the correctness guarantees it provides.
- Pact files are written locally to `/tmp/pacts/` — there is no shared Pact broker for can-i-deploy checks. A self-hosted Pact broker or Pactflow would add that capability if needed.
- E2E tests require a full Docker Compose stack and are the slowest layer. Keeping the E2E suite small is a deliberate constraint to avoid a brittle, slow feedback loop.
