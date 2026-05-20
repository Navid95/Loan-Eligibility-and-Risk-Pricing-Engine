# Database Schemas

Both services use PostgreSQL. Schemas are managed by Alembic; migrations run automatically at container startup.

---

## `rate_calculator`

### `system_rate_configs`

Singleton — exactly one row, seeded on startup.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `UUID` | PRIMARY KEY |
| `base_rate` | `NUMERIC(10,6)` | NOT NULL, CHECK `base_rate > 0` |

---

### `credit_tier_configs`

One row per credit tier (A, B, C), seeded on startup.

| Column | Type | Constraints |
|--------|------|-------------|
| `tier` | `VARCHAR(1)` | PRIMARY KEY, CHECK `tier IN ('A','B','C')` |
| `multiplier` | `NUMERIC(10,6)` | NOT NULL, CHECK `multiplier > 0` |

---

### `district_risk_configs`

One row per REGION3 district (383 rows), seeded from `data/district_risk_scores.csv`.

| Column | Type | Constraints |
|--------|------|-------------|
| `district` | `TEXT` | PRIMARY KEY |
| `multiplier` | `NUMERIC(10,6)` | NOT NULL, CHECK `multiplier > 0` |
| `region2` | `TEXT` | NOT NULL |

**Index:** `idx_district_risk_configs_region2` on `region2` — supports bulk update by region (`PUT /config/regions/{region2}`).

---

### `postal_code_mappings`

Read-only reference data seeded from `districts.csv` (22,898 rows). Never mutated after seeding.

| Column | Type | Constraints |
|--------|------|-------------|
| `postal_code` | `VARCHAR(5)` | PRIMARY KEY |
| `district` | `TEXT` | NOT NULL |
| `region1` | `TEXT` | NOT NULL |
| `region2` | `TEXT` | NOT NULL |
| `region3` | `TEXT` | NOT NULL |

---

### `outbox`

Transactional outbox for reliable RabbitMQ delivery. Rows are deleted (not flagged) after successful publish.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `UUID` | PRIMARY KEY, server default `gen_random_uuid()` |
| `correlation_id` | `UUID` | NOT NULL, UNIQUE (`uq_outbox_correlation_id`) |
| `payload` | `JSONB` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, server default `now()` |

**Index:** `idx_outbox_created_at` on `created_at` — supports relay poll order.

---

## `audit_log`

### `calculation_records`

Append-only. See immutability enforcement below.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `UUID` | PRIMARY KEY |
| `correlation_id` | `UUID` | NOT NULL, UNIQUE (`uq_calculation_records_correlation_id`) |
| `credit_tier` | `VARCHAR(1)` | NOT NULL, CHECK `credit_tier IN ('A','B','C')` |
| `district` | `TEXT` | NOT NULL |
| `base_rate` | `NUMERIC(20,6)` | NOT NULL, CHECK `base_rate > 0` |
| `term_multiplier` | `NUMERIC(20,6)` | NOT NULL |
| `credit_tier_multiplier` | `NUMERIC(20,6)` | NOT NULL |
| `regional_risk_multiplier` | `NUMERIC(20,6)` | NOT NULL |
| `final_rate` | `NUMERIC(20,6)` | NOT NULL, CHECK `final_rate > 0` |
| `calculated_at` | `TIMESTAMPTZ` | NOT NULL |
| `recorded_at` | `TIMESTAMPTZ` | NOT NULL |

**Index:** `idx_calculation_records_calculated_at` on `calculated_at` — supports date-range queries.

### Immutability enforcement

Two independent layers applied to `calculation_records`:

**1. DB permissions** — the application connects as `audit_app`, a restricted user granted SELECT and INSERT only. UPDATE, DELETE, and TRUNCATE are never granted.

**2. Statement-level trigger** (`migration 0002`) — fires unconditionally on any UPDATE attempt, including zero-row statements, regardless of the connecting user:

```sql
CREATE OR REPLACE FUNCTION raise_on_calculation_record_modification()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'calculation_records is append-only: UPDATE is not permitted';
END;
$$;

CREATE TRIGGER tg_calculation_records_immutable
    BEFORE UPDATE ON calculation_records
    FOR EACH STATEMENT
    EXECUTE FUNCTION raise_on_calculation_record_modification();
```

### Migrations

| Service | Revision | Description |
|---------|----------|-------------|
| `rate_calculator` | `0001` | Creates all five tables with constraints and indexes |
| `audit_log` | `0001` | Creates `calculation_records` with constraints and index |
| `audit_log` | `0002` | Adds `tg_calculation_records_immutable` trigger |
