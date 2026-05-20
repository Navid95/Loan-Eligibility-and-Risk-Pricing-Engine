# ADR-001: Service Boundaries

**Status:** Accepted

---

## Context

The brief requires a minimum of two independently deployable microservices with boundaries justified by the domain, not technical convenience. Boundaries driven purely by technical convenience are explicitly penalised.

The domain contains three distinct bounded contexts:

- **D1 — Rate Calculation:** Receives broker inputs, applies the loan rate formula, and returns a final rate. Ubiquitous language: applicant, loan term, credit tier, postal code, calculation request, final rate. Primary actor: partner broker.
- **D2 — Configuration & Risk Management:** Owns all business rules and configurable reference data — base rate, credit tier multipliers, regional risk index multipliers, and the postcode-to-district mapping. Ubiquitous language: base rate, multiplier, regional risk index, credit tier definition, district, postal code mapping. Primary actor: Nordvik internal admin.
- **D3 — Audit & Compliance:** Immutable record of every calculation event including all inputs and the resulting output. Ubiquitous language: audit event, calculation record, correlation ID, input snapshot, output snapshot. Primary actor: compliance/audit team.

The central question is: should any of these three contexts be co-located in a single deployable service, and if so, on what domain basis?

**Considered options:**
1. Two services — D1+D3 co-located (audit log as a calculation-time log), D2 as an independent configuration service; D1 caches multipliers locally via event-driven updates to a Redis store.
2. Two services — D1+D2 co-located, D3 as an independent audit service. *(chosen)*

---

## Decision

We define two independently deployable services:

**Service 1: `rate_calculator`** — contains D1 (Rate Calculation) and D2 (Configuration & Risk Management).

**Service 2: `audit_log`** — contains D3 (Audit & Compliance) exclusively.

### Rejection of option 1 — D1+D3 co-located, D2 independent

The alternative places D1 and D3 in one service and separates D2 as an independent configuration service. D1 would consume multiplier-change events from D2 and maintain a local Redis cache, eliminating synchronous config calls on the calculation path.

This design is rejected on three grounds:

**D3 is a compliance domain requirement, not a log generation mechanism.** A calculation-time log co-located with D1 would be application logging — operational, unstructured relative to the compliance requirement, and lacking the domain properties that D3 demands: immutability enforced at the infrastructure level, a structured query interface for auditors, and an explicit `CalculationRecord` aggregate with full input and output snapshots. Treating D3 as "a log" loses the compliance guarantee. The current design also leaves the door open for audit coverage of configuration changes — a natural auditor requirement — without architectural rework. If D3 is co-located with D1, that extension would require changes to the combined service rather than extending the dedicated audit service.

**Separating D2 introduces eventual consistency on the critical path.** In this design, a multiplier update in D2 fires an event; D1 consumes it and updates its Redis cache. Between the event being published and the cache being updated, any calculation in flight reads stale values and returns a wrong rate to a broker. The current design reads all config from the same PostgreSQL instance within the same calculation transaction, providing read-after-write consistency at no additional cost. Replacing that with an event-driven cache makes the correctness of financial output dependent on message delivery timing — an unacceptable regression for a pricing engine.

**The Redis cache adds infrastructure and a bootstrap problem.** A Redis instance is a third stateful component (alongside two PostgreSQL instances and RabbitMQ). On cold start or restart, the cache is empty; D1 requires a warm-up strategy — either a synchronous seed call to D2 or full event replay — before it can serve correct calculations. The current design has no such constraint: config is always in the database and available on first read. Adding Redis as an optimisation layer in front of a PostgreSQL source of truth is a valid future choice if calculation throughput demands it; using it as the primary store for rate-determining inputs is not.

### Justification for co-locating D1 and D2

D1 and D2 are domain-coupled in a way that makes separation architecturally dishonest rather than disciplined. D1 cannot execute a single calculation without D2's data — it needs the base rate, the credit tier multiplier for the applicant's tier, and the regional risk index multiplier for the applicant's district. They share the same ubiquitous language precisely because they operate on the same domain concepts. Separating them would produce a D1 service that holds no domain knowledge of its own and must make a synchronous remote call on every calculation request, introducing network latency and a hard runtime dependency into the critical path with no domain justification.

### Justification for separating D3 into its own service

D3 is separated on four independent domain grounds, any one of which would be sufficient:

1. **Off the critical path.** A rate must be returned to the broker regardless of what happens to the audit record. Coupling audit persistence to the calculation response would make the broker's user experience hostage to audit infrastructure health. Separation allows the rate to be returned immediately while the audit event is delivered asynchronously.

2. **Different actor and lifecycle.** D3 is owned and consumed by the compliance/audit team, not by partner brokers or Nordvik admins. It has a different release cadence, different access control requirements, and different operational characteristics (append-only, compliance-driven retention policies).

3. **Immutability as a first-class constraint.** The audit log's defining property is that records must never be modified or deleted. This constraint is best enforced at the infrastructure level (database permissions) rather than relying on application-layer guards. A dedicated service allows the database user to have INSERT-only permissions with UPDATE and DELETE explicitly revoked — a guarantee that cannot be made if the same service that writes configuration data also writes audit records.

4. **Natural fit for asynchronous integration.** The rate calculation domain emits a domain event (a rate was calculated) which the audit context consumes. This is a textbook event-driven integration between bounded contexts with different language and different concerns.

---

## Consequences

**Positive:**
- The calculation critical path has no runtime dependency on audit infrastructure.
- Audit immutability is enforced at the database permission level, not the application level.
- Each service can be scaled, deployed, and evolved independently.


**Negative / trade-offs:**
- Two services introduce operational overhead relative to a monolith (separate deployments, separate databases, a message broker).
- The audit event is delivered with eventual consistency — there is a window between a rate being returned and the audit record being committed. This is an acceptable trade-off given the separation of the critical path from audit concerns, and the audit log consumer provides at-least-once delivery guarantees via broker acknowledgement.
- If D1 and D2 ever diverge into genuinely separate bounded contexts (e.g., a dedicated admin-facing product is built), they can be split without touching the `audit_log` service.
