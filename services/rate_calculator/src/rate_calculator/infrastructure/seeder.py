import asyncio
import csv
import sys
import uuid
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.infrastructure.config import get_settings
from rate_calculator.infrastructure.database.engine import (
    create_engine,
    create_session_factory,
)
from rate_calculator.infrastructure.database.models import (
    CreditTierConfigModel,
    DistrictRiskConfigModel,
    PostalCodeMappingModel,
    SystemRateConfigModel,
)

_BATCH_SIZE = 500
_BASE_RATE = Decimal("1.03")


async def seed_base_rate(session: AsyncSession) -> None:
    # system_rate_configs holds exactly one row; the PK is an opaque UUID so we
    # select the existing row and update it, or insert if the table is empty.
    result = await session.execute(SystemRateConfigModel.__table__.select().limit(1))
    row = result.first()
    if row is None:
        await session.execute(
            insert(SystemRateConfigModel).values(id=uuid.uuid4(), base_rate=_BASE_RATE)
        )
    else:
        await session.execute(
            update(SystemRateConfigModel)
            .where(SystemRateConfigModel.id == row.id)
            .values(base_rate=_BASE_RATE)
        )
    print(f"Seeded base rate: {_BASE_RATE}")


async def seed_credit_tiers(session: AsyncSession) -> None:
    tiers = [
        {"tier": "A", "multiplier": Decimal("1.05")},
        {"tier": "B", "multiplier": Decimal("1.15")},
        {"tier": "C", "multiplier": Decimal("1.30")},
    ]
    stmt = (
        insert(CreditTierConfigModel)
        .values(tiers)
        .on_conflict_do_update(
            index_elements=["tier"],
            set_={"multiplier": insert(CreditTierConfigModel).excluded.multiplier},
        )
    )
    await session.execute(stmt)
    print("Seeded credit tiers: A=1.05, B=1.15, C=1.30")


async def seed_district_risk_configs(
    session: AsyncSession,
    csv_path: str,
    risk_scores_path: str | None = None,
) -> None:
    risk_scores: dict[str, Decimal] = {}
    if risk_scores_path is not None:
        with open(risk_scores_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                risk_scores[row["REGION3"].strip()] = Decimal(row["multiplier"].strip())

    district_rows: dict[str, dict[str, str | Decimal]] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            region3 = row["REGION3"].strip()
            region2 = row["REGION2"].strip()
            if region3 not in district_rows:
                district_rows[region3] = {
                    "district": region3,
                    "multiplier": risk_scores.get(region3, Decimal("1.0")),
                    "region2": region2,
                }

    district_list = list(district_rows.values())
    for i in range(0, len(district_list), _BATCH_SIZE):
        batch = district_list[i : i + _BATCH_SIZE]
        stmt = (
            insert(DistrictRiskConfigModel)
            .values(batch)
            .on_conflict_do_nothing(index_elements=["district"])
        )
        await session.execute(stmt)

    source = (
        f"from {risk_scores_path}"
        if risk_scores_path
        else "neutral fallback (multiplier=1.0)"
    )
    print(f"Seeded {len(district_list)} district risk configs ({source})")


async def seed_postal_code_mappings(session: AsyncSession, csv_path: str) -> None:
    # Deduplicate by postal code — the CSV has multiple rows per postcode
    # (different settlements sharing the same postcode). Last row wins.
    postcode_map: dict[str, dict[str, str]] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            postcode = row["POSTCODE"].strip()
            postcode_map[postcode] = {
                "postal_code": postcode,
                "district": row["REGION3"].strip(),
                "region1": row["REGION1"].strip(),
                "region2": row["REGION2"].strip(),
                "region3": row["REGION3"].strip(),
            }

    postcode_rows = list(postcode_map.values())

    for i in range(0, len(postcode_rows), _BATCH_SIZE):
        batch = postcode_rows[i : i + _BATCH_SIZE]
        stmt = (
            insert(PostalCodeMappingModel)
            .values(batch)
            .on_conflict_do_update(
                index_elements=["postal_code"],
                set_={
                    "district": insert(PostalCodeMappingModel).excluded.district,
                    "region1": insert(PostalCodeMappingModel).excluded.region1,
                    "region2": insert(PostalCodeMappingModel).excluded.region2,
                    "region3": insert(PostalCodeMappingModel).excluded.region3,
                },
            )
        )
        await session.execute(stmt)

    print(f"Seeded {len(postcode_rows)} postal code mappings")


async def _run(csv_path: str, risk_scores_path: str | None = None) -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        await seed_base_rate(session)
        await seed_credit_tiers(session)
        await seed_district_risk_configs(session, csv_path, risk_scores_path)
        await seed_postal_code_mappings(session, csv_path)
        await session.commit()

    await engine.dispose()


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("Usage: seed <path/to/districts.csv> [path/to/district_risk_scores.csv]")
        sys.exit(1)
    risk_scores_path = sys.argv[2] if len(sys.argv) == 3 else None
    asyncio.run(_run(sys.argv[1], risk_scores_path))
