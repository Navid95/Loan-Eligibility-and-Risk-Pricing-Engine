"""Orchestrator — chains the three modules and writes district_risk_scores.csv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from risk_model import centroid, clusterer, risk_assigner
from risk_model.risk_assigner import RiskAssignment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute geographic risk multipliers for all REGION3 boroughs."
    )
    parser.add_argument("csv_path", help="Path to districts.csv")
    parser.add_argument(
        "--output",
        default="data/district_risk_scores.csv",
        help="Output CSV path (default: data/district_risk_scores.csv)",
    )
    return parser.parse_args()


def run(csv_path: str, output_path: str) -> None:
    print(f"[1/3] Loading centroids from {csv_path} ...")
    borough_centroids = centroid.load_centroids(csv_path)
    print(f"      → {len(borough_centroids)} boroughs loaded.")

    print(f"[2/3] Running k-means clustering (k={clusterer.N_CLUSTERS}, seed={clusterer.RANDOM_SEED}) ...")
    cluster_result = clusterer.cluster_boroughs(borough_centroids)
    print("      → Cluster assignments complete.")

    print("[3/3] Assigning risk multipliers ...")
    risk_assignments = risk_assigner.assign_risk_multipliers(cluster_result, borough_centroids)
    tier_counts = _summarise_tiers(risk_assignments)
    print(f"      → Tier distribution: {tier_counts}")

    output_df = _build_output_dataframe(risk_assignments, borough_centroids)
    _assert_postconditions(output_df)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    print(f"\nDone. {len(output_df)} rows written to {output_path}")


def _build_output_dataframe(
    risk_assignments: dict[str, RiskAssignment],
    centroids: dict[str, centroid.BoroughCentroid],
) -> pd.DataFrame:
    rows = []
    for borough, assignment in risk_assignments.items():
        rows.append(
            {
                "REGION3": borough,
                "REGION2": centroids[borough]["region2"],
                "REGION1": centroids[borough]["region1"],
                "cluster_id": assignment.cluster_id,
                "east_fraction": round(assignment.east_fraction, 4),
                "multiplier": str(assignment.multiplier),
            }
        )
    return pd.DataFrame(rows, columns=["REGION3", "REGION2", "REGION1", "cluster_id", "east_fraction", "multiplier"])


def _assert_postconditions(df: pd.DataFrame) -> None:
    errors = []
    if len(df) != 383:
        errors.append(f"Expected 383 rows, got {len(df)}")
    if df["REGION3"].nunique() != len(df):
        errors.append("Duplicate REGION3 entries detected")
    if not (df["multiplier"].astype(float) > 0).all():
        errors.append("One or more multiplier values are not > 0")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


def _summarise_tiers(risk_assignments: dict[str, RiskAssignment]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for assignment in risk_assignments.values():
        label = f"{assignment.tier.value}({assignment.multiplier})"
        counts[label] = counts.get(label, 0) + 1
    return counts


if __name__ == "__main__":
    args = parse_args()
    run(args.csv_path, args.output)
