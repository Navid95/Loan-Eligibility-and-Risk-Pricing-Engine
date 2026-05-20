# ADR-003: Database Choice — audit_log Service

**Status:** Accepted

---

## Context

The `audit_log` service must persist an immutable record of every loan rate calculation event. Each record captures: the correlation ID, all calculation inputs (loan term, postal code, credit tier, and the resolved multiplier values at the time of calculation), the final rate returned, and a timestamp.

**Immutability is a hard requirement**, not a convention. This constraint must be enforced at a level deeper than application code — application-level guards can be bypassed by future developers, by bugs, or by direct database access.

**Access pattern:** Write-heavy relative to reads. Records are written continuously as calculations occur. Reads are infrequent — compliance and audit queries, typically time-range filtered, rather than transactional lookups.

**Schema characteristics:** Audit records are structurally uniform. Every record has the same fields. There is no schema variability, no nested or hierarchical data, and no requirement for full-text search or document-style queries.

**Considered options:**
1. PostgreSQL with append-only enforcement via database permissions
2. MongoDB (document store)
3. Apache Kafka (log as database)

---

## Decision

We use **PostgreSQL with layered immutability enforcement: a statement-level trigger for UPDATE, and permission-level controls for DELETE and TRUNCATE.**

### Immutability enforcement model

| Operation | Enforcement | Rationale |
|-----------|-------------|-----------|
| `UPDATE` | `BEFORE UPDATE FOR EACH STATEMENT` trigger → `RAISE EXCEPTION` | Hard block — rejects the intent regardless of how many rows the statement would affect, including zero-row updates. No escape hatch. |
| `DELETE` | Permission level — revoked from the service user; superuser only | Operational escape hatch for retention policy enforcement by a privileged operator. |
| `TRUNCATE` | Permission level — revoked from the service user; superuser only | Same rationale as DELETE. Bulk removal is an operational tool, not tampering. |

Permission-level enforcement alone is insufficient for UPDATE. A superuser connecting through any application path, an ORM misconfiguration, or a future developer bypassing application guards could silently mutate a compliance record. A trigger raises an exception at the database engine level before the write occurs — no connection credential can bypass it.

DELETE and TRUNCATE are intentionally left at the permission level because legitimate data retention policies may require purging old records. Blocking these with a trigger would make retention enforcement impossible without dropping the trigger itself, which is a more disruptive and auditable action than a superuser-only permission grant.

### Why a statement-level trigger over a row-level trigger for UPDATE

A `BEFORE UPDATE FOR EACH STATEMENT` trigger fires once per UPDATE statement regardless of how many rows the WHERE clause matches — including zero rows. A row-level trigger only fires for rows that actually match; a zero-row UPDATE would pass silently. For a compliance table, rejecting the act of attempting an update (not just updates that affect data) is the correct invariant. Statement-level is also marginally cheaper on the error path: one invocation per statement rather than N.

The trigger function requires no access to `OLD` or `NEW` row data — it unconditionally raises an exception:

```sql
CREATE OR REPLACE FUNCTION raise_on_calculation_record_modification()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'calculation_records is append-only: UPDATE is not permitted';
END;
$$;

CREATE TRIGGER tg_calculation_records_immutable
    BEFORE UPDATE ON calculation_records
    FOR EACH STATEMENT
    EXECUTE FUNCTION raise_on_calculation_record_modification();
```

### Why PostgreSQL over MongoDB

Audit records are structurally uniform — the same fields on every record. MongoDB's flexible schema is a benefit when structure is variable or unknown. Here it provides no advantage. PostgreSQL's schema constraints add value: the database will reject a malformed audit record (e.g., a null correlation ID) at write time rather than silently accepting it. For a compliance record, rejection is the correct behaviour.

### Why not Kafka as a database

Kafka's log retention can serve as a durable audit record in some architectures, but relying on it here conflates the broker's role with the persistence layer's role. The broker is transport; the database is the durable store. Kafka's retention is configurable and time-bounded by default — using it as an audit store would require careful, operationally risky configuration to ensure records are never compacted or expired. PostgreSQL with layered enforcement is a simpler, more explicit, and more auditable guarantee.

---

## Consequences

**Positive:**
- UPDATE immutability enforced at the trigger level — no credential or application path can bypass it.
- DELETE and TRUNCATE controlled at the permission level — retention policy enforcement remains possible for privileged operators without requiring schema changes.
- Trigger fires only on UPDATE attempts, which should never occur in normal operation — zero overhead on the INSERT hot path and zero overhead on reads.
- DDL operations (adding columns, creating indexes) are unaffected by DML triggers and do not interact with the immutability mechanism.
- Uniform schema enforced at the database level.
- Standard SQL interface accessible to compliance team for ad-hoc queries without engineering involvement.
- Same database technology as `rate_calculator`, reducing operational overhead (shared Docker image, same migration tooling, same monitoring approach).
- Time-range queries on `created_at` with a B-tree index are performant for the expected query patterns.

**Negative / trade-offs:**
- A superuser can drop or disable the trigger directly. This is an accepted risk: trigger removal is a deliberate, auditable DDL action — harder to do accidentally than issuing an UPDATE.
- DELETE and TRUNCATE are only prevented at the permission level. A sufficiently privileged operator can purge records. This is intentional and operationally necessary for retention policy enforcement.
- As the audit table grows, query performance on large time ranges may degrade without table partitioning. PostgreSQL declarative partitioning by month or quarter is a natural future optimisation, not needed at initial scale.
- If a future requirement introduces multiple independent consumers of audit events needing different projections (e.g., fraud detection, analytics), EventStoreDB's native projection model would become more competitive. The current design does not preclude migrating to EventStoreDB at a future point — the `audit_log` service boundary contains the change.
