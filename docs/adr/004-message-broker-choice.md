# ADR-004: Message Broker Choice

**Status:** Accepted

---

## Context

Asynchronous inter-service communication via a message broker is standard practice in microservice architecture. The `rate_calculator` service must notify the `audit_log` service of every completed calculation. This notification must be delivered reliably and handled correctly under failure conditions.

**The event type in scope** is the audit calculation event: emitted by `rate_calculator` after a rate is returned to the broker, consumed by `audit_log` to persist the immutable record. There is one producer and one consumer. Volume is proportional to calculation request traffic — human-scale for a retail loan pricing engine, not machine-scale telemetry.

**Key characteristics of this event:**

- **Consumed once, then discarded.** The audit database is the durable store. Once `audit_log` has written the record and acknowledged the message, the broker's copy has no further value. Retention is not required.
- **One consumer.** There is no fan-out requirement — no other service needs to react to this event in the current scope.
- **At-least-once delivery is required.** A missed audit record is a compliance failure. It is acceptable to receive a duplicate (idempotent write by correlation ID handles this); it is not acceptable to lose the event.
- **No ordering guarantee needed.** Audit records are timestamped. Arrival order at the consumer is irrelevant to compliance queries.
- **Low operational complexity is desirable.** The broker is infrastructure supporting one event type. Its operational overhead should be proportional to that scope.

**Events considered out of scope:**

A regional risk index feedback loop (updating multipliers based on observed default rates) was considered and rejected as out of scope. Such a loop would require loan outcome data (approvals, drawdowns, defaults) that this system does not generate or receive. The regional risk index is updated by admin API calls; no event-driven feedback mechanism is implemented. This decision is documented in ADR-006.

**Considered options:**
1. RabbitMQ
2. Apache Kafka

---

## Decision

We use **RabbitMQ**.

### Why RabbitMQ fits the audit event model

RabbitMQ's queue-based model is a direct match for the audit event's requirements:

**Message lifecycle:** RabbitMQ removes a message from the queue once the consumer issues an acknowledgement (ACK). The `audit_log` service writes the record to PostgreSQL, then ACKs. If the consumer crashes before ACKing, RabbitMQ redelivers the message to the next available consumer instance — providing at-least-once delivery without any application-level retry logic. The correlation ID on each audit record makes the consumer idempotent: a duplicate delivery results in a unique constraint violation, which is caught and discarded without corrupting state.

**Dead-letter queue (DLQ):** Messages that fail repeatedly (e.g., due to a malformed payload that cannot be deserialised) are routed to a dead-letter exchange after a configurable retry count. This prevents a poison message from blocking the queue indefinitely and provides an operator-visible failure signal.

**Failure handling and eventual consistency:** The `rate_calculator` service returns the rate to the broker before publishing the audit event. The rate response is synchronous and independent of audit delivery. If RabbitMQ is temporarily unavailable, the `rate_calculator` service should retry publication. If the broker remains unavailable, the calculation succeeds but the audit event is lost — an unacceptable outcome. To address this, a transactional outbox pattern is used: the audit event payload is written to an `outbox` table in the `rate_calculator` PostgreSQL database within the same transaction as any local state update, and a background publisher reads undelivered outbox rows and publishes them to RabbitMQ. This decouples the rate response from broker availability and guarantees that no audit event is silently lost.

### Why Kafka is not the right choice here

Kafka's defining strengths — log retention and consumer group fan-out — are not properties this system needs, and in the audit event context they become liabilities:

**Log retention is redundant.** Retaining audit events in both Kafka and PostgreSQL means the broker becomes a second source of truth for compliance data. This raises governance questions (which store is authoritative?) and increases storage costs without adding value. The audit database is the durable store; the broker is transport.

**Fan-out is not needed.** Kafka's consumer group model shines when multiple independent consumers need to process the same event stream at their own pace. With one consumer, this machinery adds configuration overhead with no benefit.

**Kafka would be the right choice if:** the system needed to feed calculation events into multiple independent consumers (e.g., a real-time fraud detection stream, an analytics pipeline, and the audit log simultaneously), or if calculation volumes were in the millions per day where Kafka's throughput advantages become relevant. Neither condition applies here, and the design can be migrated to Kafka in the future without changing the `rate_calculator` or `audit_log` service boundaries — only the broker infrastructure and publisher/consumer adapters change.

---

## Consequences

**Positive:**
- At-least-once delivery with ACK/NACK guarantees no audit events are silently lost under normal conditions.
- Dead-letter queue provides an operator-visible failure path for unprocessable messages.
- Transactional outbox pattern guarantees audit event delivery even if the broker is temporarily unavailable at calculation time.
- Message deleted after ACK — no redundant retention of audit data in the broker.

**Negative / trade-offs:**
- RabbitMQ is less suitable than Kafka if future requirements introduce multiple independent consumers of calculation events.
- The transactional outbox pattern adds a background publisher process and an outbox table to `rate_calculator`. This is a deliberate complexity trade-off to guarantee audit delivery without coupling the rate response to broker availability.
