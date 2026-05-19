# Loan Rate Engine

A microservice system that calculates personalised loan rates for retail banking customers.

## Services

| Service | Description |
|---|---|
| `rate_calculator` | Calculates loan rates and manages configuration (base rate, credit tiers, regional risk) |
| `audit_log` | Immutable record of all calculation events (in progress) |

## Prerequisites

- Docker and Docker Compose
- `districts.csv` placed under `data/` at the repository root

## Running the stack

```bash
cd infra
docker compose up --build -d
```

This starts:
- **rate-calculator** on `http://localhost:8001` (direct, no auth)
- **Kong gateway** on `http://localhost:8000` (auth required — see [Authentication](#authentication))
- **RabbitMQ management UI** on `http://localhost:15672` (user: `nordvik`, pass: `nordvik`)
- **PostgreSQL** (internal only)

Database migrations run automatically on startup.

## Seeding reference data (first run only)

On a fresh database the service starts but cannot calculate rates — reference data must be loaded once:

```bash
docker compose run --rm \
  -v "$(pwd)/../data/districts.csv:/tmp/districts.csv:ro" \
  rate-calculator \
  uv run --package rate-calculator seed /tmp/districts.csv
```

This seeds:
- Base rate: `1.03`
- Credit tiers: `A=1.05`, `B=1.15`, `C=1.30`
- 383 district risk configs (neutral multiplier `1.0`)
- 8,231 postal code mappings from `districts.csv`

Re-running the command is safe — all operations are idempotent upserts.

## API

Swagger UI is available at `http://localhost:8001/docs` (bypasses Kong, no auth required).

### Calculate a rate

```bash
curl http://localhost:8001/api/v1/rates/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -d '{"postal_code": "79100", "loan_term_months": 48, "credit_tier": "A"}'
```

## Authentication

Kong sits in front of the service on port `8000` and enforces group-based access control.

| Route | Group | Method |
|---|---|---|
| `/api/v1/rates/*` | `broker-group` | API key (`apikey` header) |
| `/api/v1/config/*` | `admin-group` | HTTP Basic Auth |

**Sample broker credentials**

| User | API key |
|---|---|
| broker-alice | `bkr-alice-a1b2c3d4e5f6` |
| broker-bob | `bkr-bob-f6e5d4c3b2a1` |

```bash
curl http://localhost:8000/api/v1/rates/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -H "apikey: bkr-alice-a1b2c3d4e5f6" \
  -d '{"postal_code": "79100", "loan_term_months": 48, "credit_tier": "A"}'
```

**Sample admin credentials**

| User | Username | Password |
|---|---|---|
| admin-carol | `admin-carol` | `carol-adm-secret` |
| admin-dave | `admin-dave` | `dave-adm-secret` |

```bash
curl http://localhost:8000/api/v1/config/system-rate \
  -u admin-carol:carol-adm-secret
```

## Stopping the stack

```bash
cd infra
docker compose down
```

To also remove persisted data (database volumes):

```bash
docker compose down -v
```

## Rate formula

```
Final Rate = Base Rate × Term Multiplier × Credit Tier Multiplier × Regional Risk Multiplier
```

| Loan term | Term multiplier |
|---|---|
| Up to 12 months | 0.8 |
| 13–36 months | 1.0 |
| 37–60 months | 1.3 |
| Above 60 months | 1.7 |

## Running tests

```bash
# Unit tests
uv run --package rate-calculator pytest services/rate_calculator/tests/unit -v

# Contract tests
uv run --package rate-calculator pytest services/rate_calculator/tests/contract -v

# Pact message tests
uv run --package rate-calculator pytest services/rate_calculator/tests/pact -v
```
