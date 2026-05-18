import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rate_calculator.infrastructure.database.models import OutboxModel
from rate_calculator.infrastructure.messaging.rabbitmq_publisher import (
    RabbitMQPublisher,
)

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: RabbitMQPublisher,
        batch_size: int = 100,
        interval_seconds: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._batch_size = batch_size
        self._interval_seconds = interval_seconds
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._relay_batch,
            trigger="interval",
            seconds=self._interval_seconds,
        )
        self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)

    async def _relay_batch(self) -> None:
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(OutboxModel)
                    .order_by(OutboxModel.created_at)
                    .limit(self._batch_size)
                )
                rows = result.scalars().all()

            for row in rows:
                try:
                    await self._publisher.publish(row.payload)
                    async with self._session_factory() as session:
                        await session.execute(
                            delete(OutboxModel).where(OutboxModel.id == row.id)
                        )
                        await session.commit()
                except Exception:
                    logger.warning(
                        "failed to relay outbox row %s — skipping",
                        row.id,
                        exc_info=True,
                    )
        except Exception:
            logger.error("outbox relay batch failed", exc_info=True)
