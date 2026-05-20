# ADR-008: Observability

**Status:** Accepted

---

## Context

Both services run as Docker containers producing output to stdout. There is no shared log aggregation infrastructure in scope for this assessment, but structured log output is a prerequisite for any future aggregation (ELK, Loki, CloudWatch, etc.).

Two concerns are in scope:

**Structured logging** — logs must be machine-parseable, carry consistent mandatory fields, and propagate the correlation ID so a single calculation event can be traced across `rate_calculator`, RabbitMQ, and `audit_log`.

**Monitoring / alerting** — out of scope for implementation at this stage. The approach is documented below for future operationalisation.

---

## Decision

### Structured logging

**Format:** JSON, emitted to stdout. A custom `_JsonFormatter` (stdlib `logging.Formatter` subclass) serialises each `LogRecord` to a JSON object. No third-party logging library is introduced.

**Mandatory fields per log record:**

| Field | Source | Example |
|---|---|---|
| `timestamp` | `record.created` → ISO-8601 UTC | `2026-05-20T10:00:00.123456+00:00` |
| `level` | `record.levelname` | `WARNING` |
| `service` | hardcoded per service in `logging_config.py` | `rate_calculator` |
| `logger` | `record.name` (module path) | `rate_calculator.infrastructure.outbox.relay` |
| `message` | `record.getMessage()` | `failed to relay outbox row …` |
| `exc_info` | formatted traceback, present only when an exception is attached | — |
| `correlation_id` | injected via `extra=` at call site, present only in HTTP request context | `3fa85f64-…` |

**Log level policy:**
- `WARNING` — recoverable failures: a 4xx HTTP response; an outbox row that fails to publish (the relay will retry it on the next poll cycle).
- `ERROR` — non-recoverable or system-level failures: a 5xx HTTP response; an unhandled exception propagating through middleware; an outbox relay batch failure; a consumer message that cannot be deserialised (routed permanently to DLQ); a consumer ACK failure.
Lower levels can be introduced based on operational needs: DEBUG for diagnosing live issues on production; INFO for statistical or operational telemetry use cases.

**Logging configuration** is applied once at process startup in each service's `main.py` by calling `configure_logging()`, which sets the root logger to WARNING with the JSON handler pointed at stdout. `uvicorn.access` is explicitly set to ERROR to suppress the per-request plain-text INFO log it would otherwise emit for every 2xx response.

**HTTP request logging middleware** is registered on each FastAPI app. It logs:
- `WARNING` on any 4xx response — includes method, path, status code, and correlation_id.
- `ERROR` on any 5xx response or unhandled exception — same fields plus exc_info where applicable.
- Nothing on 2xx/3xx responses.

**Instrumented locations:**

| Location | Service | Events logged |
|---|---|---|
| HTTP middleware | both | 4xx → WARNING; 5xx / unhandled exception → ERROR with exc_info |
| Outbox relay | `rate_calculator` | publish failure per row → WARNING with exc_info; batch failure → ERROR with exc_info |
| RabbitMQ consumer | `audit_log` | deserialisation failure → ERROR with exc_info; ACK failure → ERROR with exc_info |

The domain and application layers emit no logs. Observability belongs in the infrastructure layer.

### Monitoring (documented approach — not implemented)

A production deployment would instrument the following signals:

**`rate_calculator`:**
- Request rate and error rate on `POST /api/v1/rates/calculate` — primary SLI for broker-facing availability.
- Outbox queue depth — a sustained non-zero depth indicates broker unavailability or relay failure.
- Calculation latency (p50, p95, p99) — detects database contention or config lookup degradation.

**`audit_log`:**
- Consumer lag on `audit.calculations` queue (via RabbitMQ management API) — primary signal for audit delivery health.
- Dead-letter queue depth on `audit.calculations.dlq` — indicates permanently unprocessable messages requiring manual intervention.

**Implementation path:** `prometheus-fastapi-instrumentator` for HTTP metrics exposed at `/metrics`; a Prometheus scrape target per service; RabbitMQ's built-in Prometheus plugin for queue metrics. Alerting rules: error rate > 1% over 5 min; DLQ depth > 0.

---

## Consequences

**Positive:**
- JSON logs are immediately ingestible by any structured log aggregation tool without additional parsing.
- Correlation ID in log records links a broker request to its middleware log entry across both services.
- WARNING root level eliminates noise from third-party INFO logs without requiring per-logger configuration, with the exception of `uvicorn.access` which requires an explicit override.
- No new runtime dependency — stdlib `logging` and `json` only.

**Negative / trade-offs:**
- No monitoring implementation means there is no alerting on outbox lag or DLQ depth for this assessment. These signals are critical for production and should be the first observability investment after initial deployment.
- JSON logs are harder to read in a raw terminal than plain text. `jq` or a log viewer resolves this in practice.
- The correlation ID is only present in log records emitted within an HTTP request context (middleware). Records from the outbox relay and consumer do not carry it as a structured field — the row ID or `correlation_id` value appears in the message string only.
