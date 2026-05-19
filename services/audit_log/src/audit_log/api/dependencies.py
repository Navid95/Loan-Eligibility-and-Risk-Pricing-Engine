from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from audit_log.application.ports.calculation_record_repository import (
    CalculationRecordRepository,
)
from audit_log.infrastructure.repositories.calculation_record_repository import (
    SqlAlchemyCalculationRecordRepository,
)


def _get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory  # type: ignore[no-any-return]


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(_get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        async with session.begin():
            yield session


def get_calculation_record_repo(
    session: AsyncSession = Depends(get_session),
) -> CalculationRecordRepository:
    return SqlAlchemyCalculationRecordRepository(session)
