"""Module 3 — assign a risk multiplier to each REGION3 borough based on cluster composition."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from risk_model.centroid import BoroughCentroid
from risk_model.clusterer import ClusterResult

# Former DDR (East German) federal states. These six states have documented and
# persistent structural economic disadvantage relative to former West Germany:
# higher unemployment, lower GDP per capita, lower average household income, and
# higher emigration rates — all positively correlated with consumer credit default
# risk. Berlin is included because its post-reunification economic profile tracks
# the other former DDR states more closely than West German cities.
EAST_GERMAN_STATES: frozenset[str] = frozenset(
    {
        "Berlin",
        "Brandenburg",
        "Mecklenburg-Vorpommern",
        "Sachsen",
        "Sachsen-Anhalt",
        "Thüringen",
    }
)

# A cluster is classified East if ≥60% of its boroughs are in East German states,
# West if ≤40%, and Mixed in between. At k=6 seed=42 the actual east_fractions are
# 0.00, 0.00, 0.00, 0.02, 0.52, and 1.00 — the thresholds are deliberately wide
# to remain stable under modest k/seed variation.
EAST_THRESHOLD_HIGH: float = 0.60
EAST_THRESHOLD_LOW: float = 0.40


class ClusterTier(str, Enum):
    EAST = "east"
    MIXED = "mixed"
    WEST = "west"


# Multiplier scale rationale: the regional component is one of four compounded
# factors in the rate formula. A 30-point spread (0.90–1.20) produces ~±14%
# relative change in the regional component, translating to roughly ±1–2
# percentage points in the final annual rate at mid-range inputs — appropriate
# for a geographic signal with moderate explanatory power. West is anchored at
# 0.90 (a discount, not neutral 1.0) so prime West German boroughs are priced
# below the national mean rather than equal to it.
MULTIPLIER_SCALE: dict[ClusterTier, Decimal] = {
    ClusterTier.EAST: Decimal("1.20"),
    ClusterTier.MIXED: Decimal("1.05"),
    ClusterTier.WEST: Decimal("0.90"),
}


@dataclass(frozen=True)
class RiskAssignment:
    cluster_id: int
    east_fraction: float
    tier: ClusterTier
    multiplier: Decimal


def assign_risk_multipliers(
    cluster_result: ClusterResult,
    centroids: dict[str, BoroughCentroid],
) -> dict[str, RiskAssignment]:
    """Derive a risk multiplier for every REGION3 borough based on its cluster's
    East German composition.

    All boroughs in the same cluster receive identical multipliers. The clustering
    is the differentiating mechanism; within a cluster, geographic proximity implies
    similar risk exposure.

    Args:
        cluster_result: Output of clusterer.cluster_boroughs().
        centroids: Output of centroid.load_centroids() — used to look up REGION1.

    Returns:
        Dict mapping REGION3 name → RiskAssignment.

    Raises:
        ValueError: If any cluster_id in assignments has no members (degenerate result).
    """
    east_fractions = _compute_cluster_east_fractions(cluster_result, centroids)

    cluster_assignments: dict[int, RiskAssignment] = {}
    for cluster_id, east_fraction in east_fractions.items():
        tier = _classify_cluster(east_fraction)
        cluster_assignments[cluster_id] = RiskAssignment(
            cluster_id=cluster_id,
            east_fraction=east_fraction,
            tier=tier,
            multiplier=MULTIPLIER_SCALE[tier],
        )

    return {
        borough: cluster_assignments[cluster_id]
        for borough, cluster_id in cluster_result.assignments.items()
    }


def _classify_cluster(east_fraction: float) -> ClusterTier:
    if east_fraction >= EAST_THRESHOLD_HIGH:
        return ClusterTier.EAST
    if east_fraction <= EAST_THRESHOLD_LOW:
        return ClusterTier.WEST
    return ClusterTier.MIXED


def _compute_cluster_east_fractions(
    cluster_result: ClusterResult,
    centroids: dict[str, BoroughCentroid],
) -> dict[int, float]:
    counts: dict[int, int] = {}
    east_counts: dict[int, int] = {}

    for borough, cluster_id in cluster_result.assignments.items():
        counts[cluster_id] = counts.get(cluster_id, 0) + 1
        if centroids[borough]["region1"] in EAST_GERMAN_STATES:
            east_counts[cluster_id] = east_counts.get(cluster_id, 0) + 1

    if not counts:
        raise ValueError("No cluster assignments found — degenerate k-means result.")

    return {
        cluster_id: east_counts.get(cluster_id, 0) / total
        for cluster_id, total in counts.items()
    }
