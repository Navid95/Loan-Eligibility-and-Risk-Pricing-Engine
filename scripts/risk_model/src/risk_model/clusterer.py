"""Module 2 — group REGION3 borough centroids into spatial clusters via k-means."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans

from risk_model.centroid import BoroughCentroid

# k=6 produces exactly three tiers needed for East/West risk classification:
# 4 pure-West clusters, 1 mixed/transitional cluster, 1 pure-East cluster.
# Below 6 the transitional cluster collapses; above 6 a redundant coastal
# sliver appears with no analytical value.
N_CLUSTERS: int = 6

# Fixed seed ensures the script is deterministic across runs. n_init=10 means
# scikit-learn internally runs k-means 10 times and keeps the best result,
# covering the concern about starting-point sensitivity without manual reruns.
RANDOM_SEED: int = 42


@dataclass(frozen=True)
class ClusterResult:
    assignments: dict[str, int]                         # REGION3 → cluster_id (0-indexed)
    cluster_centroids: dict[int, tuple[float, float]]   # cluster_id → (lat, lon)


def cluster_boroughs(
    centroids: dict[str, BoroughCentroid],
    n_clusters: int = N_CLUSTERS,
    random_seed: int = RANDOM_SEED,
) -> ClusterResult:
    """Run k-means clustering on the geographic centroids of all REGION3 boroughs.

    No feature scaling is applied. Germany's lat/lon range is approximately
    isotropic (~7.5° lat, ~9° lon), and scaling would obscure the East/West
    longitude signal that anchors the political risk classification.

    Args:
        centroids: Output of centroid.load_centroids().
        n_clusters: Number of clusters k. Default 6.
        random_seed: RNG seed for KMeans. Must stay fixed across runs for
                     reproducible seeder output.

    Returns:
        ClusterResult with per-borough cluster assignment and each cluster's centroid.
    """
    boroughs = list(centroids.keys())
    coords = np.array([[centroids[b]["mean_lat"], centroids[b]["mean_lon"]] for b in boroughs])

    km = KMeans(
        n_clusters=n_clusters,
        init="k-means++",
        n_init=10,
        random_state=random_seed,
    )
    km.fit(coords)

    assignments = {borough: int(label) for borough, label in zip(boroughs, km.labels_)}
    cluster_centroids = {
        i: (float(km.cluster_centers_[i][0]), float(km.cluster_centers_[i][1]))
        for i in range(n_clusters)
    }

    return ClusterResult(assignments=assignments, cluster_centroids=cluster_centroids)
