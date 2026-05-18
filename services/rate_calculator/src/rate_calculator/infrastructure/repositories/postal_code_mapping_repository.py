from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rate_calculator.application.ports.postal_code_mapping_repository import (
    PostalCodeMappingRepository,
)
from rate_calculator.domain.entities.postal_code_mapping import PostalCodeMapping
from rate_calculator.domain.value_objects.district import District
from rate_calculator.domain.value_objects.postal_code import PostalCode
from rate_calculator.infrastructure.database.models import PostalCodeMappingModel


class SqlAlchemyPostalCodeMappingRepository(PostalCodeMappingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, postal_code: PostalCode) -> PostalCodeMapping | None:
        result = await self._session.execute(
            select(PostalCodeMappingModel).where(
                PostalCodeMappingModel.postal_code == postal_code.value
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return PostalCodeMapping(
            postal_code=PostalCode(row.postal_code),
            district=District(row.district),
            region1=row.region1,
            region2=row.region2,
            region3=row.region3,
        )
