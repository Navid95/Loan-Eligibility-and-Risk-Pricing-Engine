from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.ports.outbox_repository import OutboxRepository
from rate_calculator.application.ports.postal_code_mapping_repository import (
    PostalCodeMappingRepository,
)
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.infrastructure.repositories.credit_tier_config_repository import (
    SqlAlchemyCreditTierConfigRepository,
)
from rate_calculator.infrastructure.repositories.district_risk_config_repository import (  # noqa: E501
    SqlAlchemyDistrictRiskConfigRepository,
)
from rate_calculator.infrastructure.repositories.outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from rate_calculator.infrastructure.repositories.postal_code_mapping_repository import (
    SqlAlchemyPostalCodeMappingRepository,
)
from rate_calculator.infrastructure.repositories.system_rate_config_repository import (
    SqlAlchemySystemRateConfigRepository,
)


def _get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory  # type: ignore[no-any-return]


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(_get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        async with session.begin():
            yield session


def get_system_rate_config_repo(
    session: AsyncSession = Depends(get_session),
) -> SystemRateConfigRepository:
    return SqlAlchemySystemRateConfigRepository(session)


def get_credit_tier_config_repo(
    session: AsyncSession = Depends(get_session),
) -> CreditTierConfigRepository:
    return SqlAlchemyCreditTierConfigRepository(session)


def get_district_risk_config_repo(
    session: AsyncSession = Depends(get_session),
) -> DistrictRiskConfigRepository:
    return SqlAlchemyDistrictRiskConfigRepository(session)


def get_postal_code_mapping_repo(
    session: AsyncSession = Depends(get_session),
) -> PostalCodeMappingRepository:
    return SqlAlchemyPostalCodeMappingRepository(session)


def get_outbox_repo(
    session: AsyncSession = Depends(get_session),
) -> OutboxRepository:
    return SqlAlchemyOutboxRepository(session)
