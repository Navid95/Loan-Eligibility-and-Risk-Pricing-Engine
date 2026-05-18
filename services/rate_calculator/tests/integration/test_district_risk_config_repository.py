from decimal import Decimal

from rate_calculator.domain.aggregates.district_risk_config import DistrictRiskConfig
from rate_calculator.domain.value_objects.district import District
from rate_calculator.domain.value_objects.multiplier import Multiplier
from rate_calculator.infrastructure.database.models import DistrictRiskConfigModel
from rate_calculator.infrastructure.repositories.district_risk_config_repository import (  # noqa: E501
    SqlAlchemyDistrictRiskConfigRepository,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


def _make_config(name: str, multiplier: str = "1.0") -> DistrictRiskConfig:
    return DistrictRiskConfig(
        district=District(name), multiplier=Multiplier(Decimal(multiplier))
    )


async def _insert_with_region2(
    session: AsyncSession, district: str, region2: str, multiplier: str = "1.0"
) -> None:
    stmt = insert(DistrictRiskConfigModel).values(
        district=district, multiplier=Decimal(multiplier), region2=region2
    )
    await session.execute(stmt)


class TestSqlAlchemyDistrictRiskConfigRepository:
    async def test_save_and_get(self, session: AsyncSession) -> None:
        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        config = _make_config("München", "1.3")

        await repo.save(config)
        retrieved = await repo.get(District("München"))

        assert retrieved is not None
        assert retrieved.district == District("München")
        assert retrieved.multiplier == Multiplier(Decimal("1.3"))

    async def test_get_returns_none_for_unknown_district(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        result = await repo.get(District("Nowhere"))
        assert result is None

    async def test_list_all_pagination(self, session: AsyncSession) -> None:
        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        for name in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
            await _insert_with_region2(session, name, "TestRegion")

        page1, total = await repo.list_all(page=1, page_size=3)
        page2, _ = await repo.list_all(page=2, page_size=3)

        assert total == 5
        assert len(page1) == 3
        assert len(page2) == 2

    async def test_list_by_region2_filters_correctly(
        self, session: AsyncSession
    ) -> None:
        await _insert_with_region2(session, "Freiburg-Stadt", "Freiburg")
        await _insert_with_region2(session, "Breisgau", "Freiburg")
        await _insert_with_region2(session, "Emmendingen", "Freiburg")
        await _insert_with_region2(session, "München", "Oberbayern")
        await _insert_with_region2(session, "Dachau", "Oberbayern")

        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        results = await repo.list_by_region2("Freiburg")

        assert len(results) == 3
        names = {r.district.name for r in results}
        assert names == {"Freiburg-Stadt", "Breisgau", "Emmendingen"}

    async def test_save_many(self, session: AsyncSession) -> None:
        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        configs = [_make_config(f"District{i}") for i in range(5)]

        await repo.save_many(configs)

        for config in configs:
            retrieved = await repo.get(config.district)
            assert retrieved is not None

    async def test_save_many_upserts_multiplier(self, session: AsyncSession) -> None:
        repo = SqlAlchemyDistrictRiskConfigRepository(session)
        await repo.save(_make_config("Karlsruhe", "1.0"))

        await repo.save_many([_make_config("Karlsruhe", "1.8")])

        retrieved = await repo.get(District("Karlsruhe"))
        assert retrieved is not None
        assert retrieved.multiplier == Multiplier(Decimal("1.8"))
