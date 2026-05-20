# ADR-005: Security

**Status:** Accepted

---

## Context

The brief requires that the API be authenticated and that security design cover authentication, audit logging, and data handling. Three distinct actor groups interact with the system:

**Partner brokers** — external companies integrating via API to request loan rates on behalf of applicants. This is a business-to-business (B2B) machine-to-machine (M2M) integration pattern. Each broker is a named organisational entity, not an individual user. Multiple brokers are onboarded independently, each requiring their own revocable identity. Brokers interact exclusively with the rate calculation API.

**Nordvik internal admins** — a small, trusted population managing base rate, credit tier multipliers, and regional risk index configuration via the config API on the `rate_calculator` service.

**Compliance/audit team** — Nordvik internal staff who query the immutable calculation record via the `audit_log` service. This is a read-only access surface; no write endpoints are exposed over HTTP.

**The Onion Architecture constraint shapes the auth decision.** The domain layer must have zero dependencies on infrastructure or frameworks. Authentication is infrastructure — it is a cross-cutting concern that belongs at the system's edge, not inside any individual service's domain or application layer. Placing an auth middleware inside `rate_calculator` would embed an infrastructure concern in the application layer, which violates the architectural constraint.

**Considered approaches:**
1. API key validation middleware inside `rate_calculator` (application-layer auth)
2. API gateway handling authentication at the edge (infrastructure-layer auth)

---

## Decision

We use **Kong Gateway OSS** (Apache 2.0 licence — free) as an API gateway in front of both services. Kong handles all authentication and cross-cutting concerns at the edge. Neither service's domain layer contains any authentication code.

### Kong Gateway OSS in DB-less / declarative mode

Kong runs as a single Docker container with no external coordination dependencies. In DB-less mode, the entire gateway configuration — routes, services, consumers, plugins — is declared in a `kong.yml` file committed to the repository. There is no Kong database, no admin UI dependency, and no runtime state to manage. The configuration is version-controlled and reproducible.

**Kong handles authentication across three routes:**

**Broker-facing route (`/api/v1/rates`)** — `key-auth` plugin validates the `apikey` header against declared consumers. Invalid or missing keys receive a 401 before the request reaches `rate_calculator`. An ACL plugin restricts access to the `broker-group`. Credentials are stripped before the request is proxied (`hide_credentials: true`). A `rate-limiting` plugin enforces a static limit of 60 requests per minute per consumer (`limit_by: consumer`, `policy: local`), returning 429 on breach. Each broker has an independent bucket; the `local` policy uses in-memory counters and requires no additional infrastructure for a single-node deployment.

**Admin-facing route (`/api/v1/config`)** — `basic-auth` plugin validates HTTP Basic Auth credentials against declared consumers. An ACL plugin restricts access to the `admin-group`. Credentials are stripped before the request is proxied.

**Auditor-facing route (`/api/v1/records`)** — `basic-auth` plugin with ACL restricting to the `auditor-group`. Routes to the `audit_log` service. Credentials are stripped before the request is proxied.

**Correlation ID injection** — Kong injects an `X-Correlation-Id` header on every inbound request to `rate_calculator` (using the `correlation-id` plugin with a UUID generator), overwriting any client-supplied value and echoing it in the response. This header becomes the correlation ID that flows through `rate_calculator` and into the audit record. The observability requirement for a consistent correlation ID across services is satisfied at the gateway layer, not in the application.

**Routing** — Kong routes `/api/v1/rates` and `/api/v1/config` to `rate_calculator`; `/api/v1/records` to `audit_log`. Each route carries its own auth plugin and ACL configuration, enforcing the correct credential type and consumer group per surface.

### Services and consumers

All three actor groups are declared as Kong consumers in `kong.yml`:

| Consumer | Auth type | Consumer group | Upstream service |
|---|---|---|---|
| `broker-alice`, `broker-bob` | key-auth (`apikey` header) | `broker-group` | `rate_calculator` |
| `admin-carol`, `admin-dave` | basic-auth | `admin-group` | `rate_calculator` |
| `auditor-alice` | basic-auth | `auditor-group` | `audit_log` |

### Service domain layers

The domain and application layers of both services contain no authentication code. Each service trusts that Kong has authenticated the caller before the request reaches it — this trust is justified because the only path to either service is through Kong.

This is the correct Onion Architecture outcome: the domain layer is decoupled from the mechanism by which identity is established. If Kong is replaced by a different gateway, or if additional identity claims are added, the domain layers are unaffected.

### Why API keys over JWT

The broker integration is the textbook API key use case, and JWT's strengths do not apply:

**JWT's primary advantage is stateless validation** via asymmetric signatures — a service can verify a token without a database lookup, using a distributed public key. This benefit is relevant when tokens cross many independent trust boundaries. Here, Kong is the single trust boundary; stateless validation is not a problem that needs solving.

**The M2M JWT equivalent is OAuth 2.0 client_credentials flow**, which requires an authorisation server (an external identity provider, or a custom issuing endpoint), a token round-trip before each API session, and token expiry and refresh management. For a broker integrating a loan rate lookup, this is operational overhead with no functional benefit over a stable API key that Kong validates natively.

**Token expiry creates operational risk for B2B integrations.** A broker whose access token expires during a live customer interaction will receive a 401 on a production request. API keys do not expire; they are revoked deliberately by an operator. For a financial pricing API where predictable availability is critical, this is the correct trade-off.

**Direct per-partner attribution.** Each key uniquely identifies a broker. If a key is compromised, exactly one partner is affected and exactly one credential is revoked in Kong. In a JWT scheme with shared client secrets, the blast radius of a compromise is harder to contain.

**JWT would be the right choice if:** Nordvik already operated a centralised identity provider (Keycloak, Auth0) that other internal systems integrated with, making JWT a zero-cost addition; or if the optional customer-facing web UI were in scope, which would require OAuth 2.0 authorisation code flow with PKCE for user session management — a different auth surface from the broker API that would use short-lived JWTs issued by the gateway or an IDP.

---

## Input validation and sanitisation

All request bodies received by `rate_calculator` are validated against Pydantic models at the API boundary before any domain logic executes. Validation failures return 422 with structured error detail. The postal code field is validated against the 5-digit numeric German format; the credit tier field is validated against the enumerated set of configured tiers; the loan term field is validated as a positive integer. No raw user input reaches the domain layer or the database without passing schema validation. Kong provides a first layer of defence (routing and auth); Pydantic provides a second layer at the application boundary.

Incoming RabbitMQ event payloads consumed by `audit_log` are validated through domain VO construction rather than a schema layer. The consumer parses the raw JSON body and passes each field directly into domain value objects (`UUID`, `CreditTier`, `Rate`, `Multiplier`, `District`, `datetime.fromisoformat`). Any failure — malformed JSON, missing field, type mismatch, or a domain VO invariant violation — is treated as a permanent failure: the message is NACK'd without requeue and routed to the dead-letter queue. No invalid data reaches the domain layer or the database.

---

## Data handling and GDPR awareness

**Postal code as location PII.** A German 5-digit postal code is location data and constitutes personal data under GDPR when combined with other context that could identify an individual. Postal code is a necessary input to the rate calculation but is never persisted — it is resolved to a REGION3 district in the application layer, and only the district name (e.g., "Breisgau-Hochschwarzwald") is stored in the audit record. A REGION3 borough covers a population of tens of thousands; it is a coarser geographic granularity than a postal code and does not on its own identify an individual. This is a deliberate data minimisation choice aligned with GDPR Article 5(1)(c): the system retains the least precise location representation necessary for compliance and risk auditability. Nordvik never receives the applicant's name, identity document, or other direct identifiers — the broker, as the data controller for the applicant relationship, abstracts this. The audit record contains only the inputs required for the calculation.

**Audit log retention.** A retention policy for audit records must be defined by the compliance team and is not encoded in the application. Enforcing retention (e.g., archiving records older than N years) requires an explicit operational process with elevated database privileges, subject to the compliance team's direction. This gap is noted for the operational runbook.

**Transport security.** All external communication — between brokers and Kong, and between Kong and the upstream services — must be TLS-encrypted. In the local assessment setup, TLS termination is omitted for simplicity and Kong proxies over plain HTTP to both services within the Docker network. In a production deployment, Kong handles TLS termination at the edge; internal service-to-service traffic may use mutual TLS or rely on network-level controls within the cluster.

---

## Consequences

**Positive:**
- Authentication is infrastructure: neither service's domain layer has auth code, consistent with Onion Architecture.
- Cross-cutting concerns (correlation ID, key auth, basic auth, ACL) are handled once at the edge — not duplicated per service.
- Kong Gateway OSS is free (Apache 2.0), well-documented, and has a mature Docker Compose setup.
- Key revocation is immediate and operational: Kong Admin API or declarative config reload, no application redeployment.
- Adding a new broker, admin, or auditor is a gateway configuration change, not an application change.
- Per-broker rate limiting is enforced at the gateway — no application code required, and each broker's quota is independent.

**Negative / trade-offs:**
- Kong adds one container to Docker Compose. The local setup requires Kong to be healthy before requests can be made. This is mitigated by standard Docker Compose `depends_on` health checks.
- DB-less declarative mode means credential changes (for the assessment) require a config file edit and a Kong reload (`kong reload`), not a runtime API call. For production, Kong Admin API removes this limitation — the ADR notes both paths.
- The admin and auditor routes rely on HTTP Basic Auth, which transmits credentials on every request. In production this must be combined with TLS termination at Kong to prevent credential exposure in transit.
- The `rate-limiting` plugin uses `policy: local` (in-memory counters per Kong node). In a multi-node production deployment this must be switched to `policy: redis` with a shared Redis instance; otherwise each node maintains its own counter and the effective limit per broker becomes `60 × number_of_nodes`.
- If a future requirement introduces user-facing authentication (customer web UI, OAuth login), a second auth surface is needed — Kong supports this via an OIDC plugin alongside the existing key-auth plugin, so the gateway handles both without application changes.
