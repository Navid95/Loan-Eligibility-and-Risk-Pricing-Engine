"""Module 1 — compute the geographic centre of gravity for each REGION3 borough."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd


class BoroughCentroid(TypedDict):
    region1: str
    region2: str
    mean_lat: float
    mean_lon: float


def load_centroids(csv_path: str | Path) -> dict[str, BoroughCentroid]:
    """Read districts.csv and compute a geographic centroid for each REGION3 borough.

    Groups all rows by REGION3, takes the arithmetic mean of LATITUDE and LONGITUDE
    within the group, and carries forward the unique REGION1 and REGION2 values.

    Args:
        csv_path: Path to districts.csv.

    Returns:
        Dict mapping each REGION3 name to its BoroughCentroid. Guaranteed to contain
        exactly one entry per unique REGION3 in the CSV (383 for the unmodified file).

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If any REGION3 has inconsistent REGION1 or REGION2 values across
                    rows — guards against data corruption.
    """
    df = pd.read_csv(
        csv_path,
        dtype={
            "REGION1": str,
            "REGION2": str,
            "REGION3": str,
            "REGION4": str,
            "POSTCODE": str,
            "SETTLEMENT": str,
        },
        usecols=["REGION1", "REGION2", "REGION3", "LATITUDE", "LONGITUDE"],
    )

    _assert_region_consistency(df, "REGION1")
    _assert_region_consistency(df, "REGION2")

    coords = (
        df.groupby("REGION3", sort=False)
        .agg(mean_lat=("LATITUDE", "mean"), mean_lon=("LONGITUDE", "mean"))
        .reset_index()
    )

    meta = df.groupby("REGION3", sort=False)[["REGION1", "REGION2"]].first().reset_index()
    merged = coords.merge(meta, on="REGION3")

    result: dict[str, BoroughCentroid] = {}
    for row in merged.itertuples(index=False):
        result[row.REGION3] = BoroughCentroid(
            region1=row.REGION1,
            region2=row.REGION2,
            mean_lat=float(row.mean_lat),
            mean_lon=float(row.mean_lon),
        )

    return result


def _assert_region_consistency(df: pd.DataFrame, column: str) -> None:
    inconsistent = df.groupby("REGION3")[column].nunique()
    violations = inconsistent[inconsistent > 1]
    if not violations.empty:
        raise ValueError(
            f"Data integrity error: REGION3 entries with inconsistent {column} values: "
            f"{violations.index.tolist()}"
        )
