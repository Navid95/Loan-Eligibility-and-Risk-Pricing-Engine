# ADR-006: Regional Risk Index

**Status:** Accepted

---

## Context

The brief requires a regional risk index representing *"the likelihood of default based on where the applicant lives."* This index is one of four multiplicative factors in the rate formula:

```
Final Annual Rate (%) = Base Rate
                      × Multiplier(Loan Term)
                      × Multiplier(Credit Tier)
                      × Multiplier(Regional Risk Index)
```

The index must be configurable at runtime without redeployment — Nordvik internal admins update it via the `PUT /api/v1/config/districts/{district}` and `PUT /api/v1/config/regions/{region2}` endpoints. The granularity at which it is configured is **REGION3** (383 German boroughs).

**The problem:** no outcome data is provided. There is no historical loan portfolio, no default rate series, no income or unemployment statistics, and no external credit bureau data. The only data available is `districts.csv` — a geographic reference file containing 22,898 rows of German postal codes with the following fields relevant to the risk model:

| Field | Description |
|---|---|
| `REGION1` | Federal state (16 Bundesländer) |
| `REGION2` | Administrative region (29 total) |
| `REGION3` | Borough/municipality (383 unique values — the index granularity) |
| `LATITUDE` | Decimal latitude of each postcode/settlement |
| `LONGITUDE` | Decimal longitude of each postcode/settlement |

**What this means in practice:** it is impossible to derive an empirically grounded default probability from this data. There are no outcome labels to regress against. Any initial index values are necessarily synthetic — a structured approximation rather than a measurement. The seeded values are a starting point that Nordvik's risk team is expected to refine using actual portfolio data once available.

**Requirements on the initial seed:**
- All 383 REGION3 boroughs must have a multiplier > 0 at system startup.
- The model must be deterministic — running the seeding script twice must produce identical output.

**Events considered out of scope:**

A regional risk feedback loop — updating multipliers automatically based on observed default rates — was considered and rejected. Such a loop would require loan outcome data (approvals, drawdowns, defaults) that this system does not generate or receive. The broker-facing API returns rates; it does not record decisions or outcomes. The index is updated by admin API calls; no automated feedback mechanism is implemented.

**Considered options:**
1. Uniform baseline — all 383 boroughs seeded with 1.0
2. Settlement density proxy — row count per REGION3 as a crude urbanisation proxy
3. Geographic clustering with East/West economic anchoring

---

## Decision

We use **geographic clustering with East/West Germany economic anchoring**.

The model groups all 383 REGION3 boroughs into spatial clusters using k-means on their geographic centroids, then assigns a risk tier to each cluster based on the proportion of its boroughs that belong to former East German federal states. A three-tier multiplier scale (0.90 / 1.05 / 1.20) is applied per tier.

The model is implemented as a standalone analytical script at `scripts/risk_model/` and produces `data/district_risk_scores.csv` — 383 rows, one per REGION3, consumed by the seeder.

### Model specification

**Clustering parameters:**
- Algorithm: k-means++ initialisation, `n_init=10` (scikit-learn runs 10 independent initialisations and keeps the best result, mitigating starting-point sensitivity)
- `k=6` clusters, `random_seed=42` — fixed for determinism
- No feature scaling applied: Germany's lat/lon range is approximately isotropic (~7.5° latitude, ~9° longitude), and scaling would suppress the East/West longitude signal that anchors the risk classification
- At k=6 seed=42, the six clusters break down as: 4 pure-West clusters (east fraction ≈ 0.00, 0.00, 0.00, 0.02), 1 transitional cluster (east fraction ≈ 0.52), 1 pure-East cluster (east fraction = 1.00)

**East German states (REGION1):** Brandenburg, Mecklenburg-Vorpommern, Sachsen, Sachsen-Anhalt, Thüringen, and Berlin. Berlin is included because its post-reunification economic profile — unemployment rate, GDP per capita, household income, emigration — tracks the other former DDR states more closely than West German cities.

**Tier classification:** each cluster's East German fraction (proportion of its REGION3 boroughs whose REGION1 is in the East German set) determines its tier:

| East fraction | Tier | Multiplier |
|---|---|---|
| ≥ 60% | East | 1.20 |
| 41–59% | Mixed | 1.05 |
| ≤ 40% | West | 0.90 |

The thresholds (60% / 40%) are deliberately wide to remain stable under modest variation in k or seed. At the actual cluster fractions (0.00, 0.00, 0.00, 0.02, 0.52, 1.00), both thresholds are comfortably satisfied — no cluster sits near a boundary.

**Multiplier scale rationale:** the regional component is one of four compounded factors in the rate formula. The 30-point spread (0.90–1.20) produces approximately ±14% relative variation in the regional component, translating to roughly ±1–2 percentage points in the final annual rate at mid-range inputs — appropriate for a geographic signal with moderate explanatory power. West is anchored at 0.90 rather than a neutral 1.0 so that prime West German boroughs are priced below the national mean, not equal to it.

### Why geographic clustering over a uniform baseline

A uniform baseline (all boroughs at 1.0) is intellectually honest but contributes nothing at launch. The regional risk index becomes a no-op until manually configured, which places the full burden of differentiating 383 boroughs on admin judgment without any structural starting point. Geographic clustering provides a principled, documentable, spatially coherent initial state — one that admins can reason about and override with confidence, rather than facing a blank sheet.

### Why geographic clustering over settlement-density proxy

Settlement density (row count per REGION3 in the CSV) is derived entirely from the data without external assumptions. However, it has two structural weaknesses that make it inferior to geographic clustering.

First, CSV row count is not population density. It reflects how Germany draws postal district boundaries — a function of administrative history, not how many people live in an area. Dense urban cores and sparse rural areas can appear indistinguishable if their borough boundaries happen to contain similar numbers of postcode entries.

Second, the direction of the effect is genuinely ambiguous. Whether more settlements implies higher or lower default risk is unknown without outcome data, and any direction assumed must be documented as an arbitrary choice. Geographic clustering, by contrast, anchors its risk assignment to the East/West economic divide — a documented structural fact, not an assumed direction.


### The index as a structured starting point

The seeded values are not a measurement of default likelihood. They are a structured, geographically coherent, documentable starting configuration that gives Nordvik's risk team a reasonable basis from which to begin runtime calibration.

The expectation is that as loan portfolio data accumulates — actual defaults, repayment behaviour, regional concentration — the risk team updates multipliers via the admin API using real evidence. The clustering model serves its purpose at system bootstrap; it is not intended to remain the operative model indefinitely.

---

## Consequences

**Positive:**
- All 383 boroughs have a differentiated, non-arbitrary starting multiplier at system launch — the regional risk index is functional from day one.
- Spatial coherence: geographically adjacent boroughs receive the same multiplier, which is the correct default assumption in the absence of more granular data.
- The East/West rationale is a publicly documented, well-understood structural fact about Germany — not an opaque algorithmic output.
- The model is fully deterministic and reproducible: running `scripts/risk_model/` at any point in the future on the same input CSV produces identical output.
- All seeded values are immediately overridable at runtime without redeployment, via the existing admin API endpoints.
- The standalone script (`scripts/risk_model/`) is isolated from service packages — its ML dependencies (pandas, scikit-learn, numpy) do not enter the service codebase or workspace lock file.

**Negative / trade-offs:**

- **The model is synthetic, not empirical.** The risk scores are derived from geography alone. There is no outcome variable, no validation set, and no way to measure predictive accuracy until portfolio data exists. The index should be treated as an administrative default, not a risk measurement.

- **Geographic proxies for credit risk have legal sensitivity.** In regulated lending markets, using an applicant's location as a direct risk factor can constitute indirect discrimination if that location correlates with protected characteristics (ethnicity, nationality). The regional risk index as implemented is a configuration starting point for Nordvik's internal risk team, not a consumer-facing pricing rule derived automatically from location. Nordvik's compliance function should review the multipliers before they become operative in production, and the legal basis for geographic risk differentiation should be established under the applicable regulatory framework.

- **Known border cases.** At k=6 with seed=42, two classes of geographic edge case arise: one Mecklenburg-Vorpommern borough (coastal, clusters with the North-West West group) receives multiplier 0.90 rather than the 1.20 that other MV boroughs receive; and 11 Bayern boroughs (alpine south-east, geographically proximate to the Czech and Austrian borders) receive 1.05 rather than 0.90. These are genuine geographic ambiguities — boroughs at cluster boundaries where the East/West classification is contestable. They are the natural candidates for early admin override once the system is operational.

- **Thüringen is predominantly Mixed (1.05), not East (1.20).** Thüringen straddles the former inner-German border and its REGION3 boroughs cluster with the transitional Mixed group. This is geographically accurate but may understate risk relative to the other former DDR states. Nordvik's risk team should review Thüringen multipliers explicitly when calibrating the index.

- **k and seed are fixed parameters, not learned.** The number of clusters (6) and the random seed (42) are documented choices, not optimised hyperparameters. If Nordvik's data team wishes to re-derive the seed values using a more rigorous cluster quality metric, the script supports this by accepting `n_clusters` and `random_seed` as parameters. The current values are recommended defaults; changing them changes the cluster boundaries and therefore which boroughs fall into which tier.
