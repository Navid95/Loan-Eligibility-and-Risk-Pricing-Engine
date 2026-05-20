# ADR-002: Database Choice — rate_calculator Service

**Status:** Accepted

---

## Context

The `rate_calculator` service must persist the following entities:

- **System configuration** — a single base rate value, system-wide.
- **Credit tier definitions** — a finite set of named tiers (e.g., A, B, C, D), each with a configurable multiplier.
- **Regional risk index configuration** — a multiplier per REGION3 borough (383 distinct values derived from the district reference data).
- **Postcode-to-district mapping** — 22,898 rows mapping German postal codes to their REGION3 borough, seeded from `districts.csv` at startup.

**Read/write profile:** Configuration data is read on every calculation request and written only when an admin updates a value. The postcode mapping is read-only after initial seed. This is a high-read, low-write workload.

**Consistency requirements:** Financial calculations must be based on a consistent, point-in-time snapshot of configuration. A calculation must not observe a partial update where some multipliers have changed and others have not within a single request. ACID transaction guarantees are required.

**Query pattern:** The core lookup path is: postcode → REGION3 → regional risk index multiplier. This is a foreign-key join across two tables — a pattern that relational databases are purpose-built for.

**Considered options:**
1. PostgreSQL (relational, SQL)
2. MongoDB (document store, NoSQL)
3. Redis (in-memory key-value store)

---

## Decision

We use **PostgreSQL**.

### Why PostgreSQL over MongoDB

The data in this service is structured, typed, and relationally organised. The postcode-to-district mapping has a clear many-to-one relationship with the regional risk index configuration (many postcodes map to one REGION3; one REGION3 has one risk multiplier). Modelling this as documents would require either denormalisation (duplicating the multiplier into every postcode row, requiring bulk updates on every config change) or embedded references that replicate relational joins in application code. Neither is an improvement over a foreign key.

MongoDB's flexible schema is a benefit when data structure is uncertain or highly variable. Here, the schema is fully known, stable, and benefits from type constraints (e.g., multiplier must be a positive decimal, not a string or null). PostgreSQL's schema validation enforces this at the database level.

ACID transactions are first-class in PostgreSQL. If an admin updates the base rate and several credit tier multipliers in a single operation, all changes must be visible atomically to calculation requests. MongoDB's multi-document transactions exist but carry additional overhead and are not idiomatic.

### Why PostgreSQL over Redis

Redis is an appropriate choice as a caching layer in front of the database (and could be added later to reduce lookup latency), but it is not suitable as the primary store for this service. Redis does not provide durable, queryable relational storage. It has no foreign key support, no SQL query interface. Using Redis as a primary store would require the application to manage relational integrity that the database should enforce.

### Why PostgreSQL specifically (over other RDBMS options)

PostgreSQL is chosen over MySQL/MariaDB and SQLite on the following grounds:

- **Production maturity for financial workloads:** PostgreSQL has strong support for decimal arithmetic without floating-point precision loss, which matters for multiplier storage and rate calculations.
- **Python ecosystem:** `asyncpg` provides a high-performance async driver; SQLAlchemy with async support and Alembic for migrations are both well-established against PostgreSQL.

---

## Consequences

**Positive:**
- Relational integrity enforced at the database level (foreign keys, type constraints).
- ACID transactions guarantee consistent snapshots for calculations.
- The postcode-to-district lookup is a single indexed join — performant and simple.
- Schema migrations managed with Alembic provide a clear audit trail of data model changes.
- Strong Python tooling (SQLAlchemy, asyncpg, Alembic) with production-grade async support.

**Negative / trade-offs:**
- PostgreSQL requires more operational overhead than a simple key-value store (connection pooling, vacuum, schema migrations). For this domain's data volumes and access patterns, this overhead is justified.
- If calculation throughput scales significantly, the postcode lookup becomes a hot read path. A Redis cache in front of the regional risk index configuration is a natural future optimisation — the PostgreSQL store remains the source of truth and the cache is invalidated on admin config updates.
