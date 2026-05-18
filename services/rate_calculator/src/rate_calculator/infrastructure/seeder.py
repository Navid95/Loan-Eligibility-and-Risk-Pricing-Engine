import asyncio
import csv
import sys
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert

from rate_calculator.infrastructure.config import get_settings
from rate_calculator.infrastructure.database.engine import (
    create_engine,
    create_session_factory,
)
from rate_calculator.infrastructure.database.models import (
    DistrictRiskConfigModel,
    PostalCodeMappingModel,
)

_BATCH_SIZE = 500
_DEFAULT_MULTIPLIER = Decimal("1.0")


async def _seed(csv_path: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    postcode_rows: list[dict[str, str | Decimal]] = []
    district_rows: dict[str, dict[str, str | Decimal]] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            postcode = row["POSTCODE"].strip()
            region1 = row["REGION1"].strip()
            region2 = row["REGION2"].strip()
            region3 = row["REGION3"].strip()

            postcode_rows.append(
                {
                    "postal_code": postcode,
                    "district": region3,
                    "region1": region1,
                    "region2": region2,
                    "region3": region3,
                }
            )

            if region3 not in district_rows:
                district_rows[region3] = {
                    "district": region3,
                    "multiplier": _DEFAULT_MULTIPLIER,
                    "region2": region2,
                }

    async with session_factory() as session:
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

        district_list = list(district_rows.values())
        for i in range(0, len(district_list), _BATCH_SIZE):
            batch = district_list[i : i + _BATCH_SIZE]
            stmt = (
                insert(DistrictRiskConfigModel)
                .values(batch)
                .on_conflict_do_nothing(index_elements=["district"])
            )
            await session.execute(stmt)

        await session.commit()

    await engine.dispose()
    print(f"Seeded {len(postcode_rows)} postal codes, {len(district_rows)} districts.")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: seed-districts <path/to/districts.csv>")
        sys.exit(1)
    asyncio.run(_seed(sys.argv[1]))
