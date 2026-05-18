from rate_calculator.domain.entities.postal_code_mapping import PostalCodeMapping
from rate_calculator.domain.value_objects.district import District
from rate_calculator.domain.value_objects.postal_code import PostalCode
from rate_calculator.infrastructure.database.models import PostalCodeMappingModel
from rate_calculator.infrastructure.repositories.postal_code_mapping_repository import (
    SqlAlchemyPostalCodeMappingRepository,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


async def _insert_mapping(session: AsyncSession) -> None:
    stmt = insert(PostalCodeMappingModel).values(
        postal_code="79189",
        district="Breisgau-Hochschwarzwald",
        region1="Baden-Württemberg",
        region2="Freiburg",
        region3="Breisgau-Hochschwarzwald",
    )
    await session.execute(stmt)


class TestSqlAlchemyPostalCodeMappingRepository:
    async def test_get_returns_mapping(self, session: AsyncSession) -> None:
        await _insert_mapping(session)
        repo = SqlAlchemyPostalCodeMappingRepository(session)

        result = await repo.get(PostalCode("79189"))

        assert result is not None
        assert result.postal_code == PostalCode("79189")
        assert result.region1 == "Baden-Württemberg"
        assert result.region2 == "Freiburg"
        assert result.region3 == "Breisgau-Hochschwarzwald"

    async def test_get_returns_none_for_unknown_postal_code(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPostalCodeMappingRepository(session)
        result = await repo.get(PostalCode("00000"))
        assert result is None

    async def test_district_value_object_is_correct(
        self, session: AsyncSession
    ) -> None:
        await _insert_mapping(session)
        repo = SqlAlchemyPostalCodeMappingRepository(session)

        result = await repo.get(PostalCode("79189"))

        assert isinstance(result, PostalCodeMapping)
        assert result.district == District("Breisgau-Hochschwarzwald")
