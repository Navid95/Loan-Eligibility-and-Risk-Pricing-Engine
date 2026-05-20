from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.domain.aggregates.district_risk_config import DistrictRiskConfig
from rate_calculator.domain.value_objects.district import District
from rate_calculator.domain.value_objects.multiplier import Multiplier
from rate_calculator.infrastructure.database.models import DistrictRiskConfigModel


def _to_domain(row: DistrictRiskConfigModel) -> DistrictRiskConfig:
    return DistrictRiskConfig(
        district=District(row.district), multiplier=Multiplier(row.multiplier)
    )


class SqlAlchemyDistrictRiskConfigRepository(DistrictRiskConfigRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, district: District) -> DistrictRiskConfig | None:
        result = await self._session.execute(
            select(DistrictRiskConfigModel).where(
                DistrictRiskConfigModel.district == district.name
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def list_all(
        self, *, page: int, page_size: int
    ) -> tuple[list[DistrictRiskConfig], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(DistrictRiskConfigModel)
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self._session.execute(
            select(DistrictRiskConfigModel)
            .order_by(DistrictRiskConfigModel.district)
            .limit(page_size)
            .offset(offset)
        )
        items = [_to_domain(row) for row in result.scalars()]
        return items, total

    async def list_by_region2(self, region2: str) -> list[DistrictRiskConfig]:
        result = await self._session.execute(
            select(DistrictRiskConfigModel)
            .where(DistrictRiskConfigModel.region2 == region2)
            .order_by(DistrictRiskConfigModel.district)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, config: DistrictRiskConfig) -> None:
        stmt = (
            insert(DistrictRiskConfigModel)
            .values(
                district=config.district.name,
                multiplier=config.multiplier.value,
                region2="",
            )
            .on_conflict_do_update(
                index_elements=["district"],
                set_={"multiplier": config.multiplier.value},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def save_many(self, configs: list[DistrictRiskConfig]) -> None:
        if not configs:
            return
        stmt = (
            update(DistrictRiskConfigModel)
            .where(
                DistrictRiskConfigModel.district.in_(
                    [c.district.name for c in configs]
                )
            )
            .values(
                multiplier=case(
                    *[
                        (
                            DistrictRiskConfigModel.district == c.district.name,
                            c.multiplier.value,
                        )
                        for c in configs
                    ]
                )
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
