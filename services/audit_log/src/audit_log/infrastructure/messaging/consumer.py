import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate
from audit_log.infrastructure.repositories.calculation_record_repository import (
    SqlAlchemyCalculationRecordRepository,
)

logger = logging.getLogger(__name__)


def _deserialise(payload: dict[str, str], recorded_at: datetime) -> CalculationRecord:
    return CalculationRecord(
        correlation_id=UUID(payload["correlation_id"]),
        credit_tier=CreditTier(payload["credit_tier"]),
        district=District(payload["district"]),
        base_rate=Rate(Decimal(payload["base_rate"])),
        term_multiplier=Multiplier(Decimal(payload["term_multiplier"])),
        credit_tier_multiplier=Multiplier(Decimal(payload["credit_tier_multiplier"])),
        regional_risk_multiplier=Multiplier(
            Decimal(payload["regional_risk_multiplier"])
        ),
        final_rate=Rate(Decimal(payload["final_rate"])),
        calculated_at=datetime.fromisoformat(payload["calculated_at"]),
        recorded_at=recorded_at,
    )


class AuditEventConsumer:
    def __init__(
        self,
        *,
        rabbitmq_url: str,
        queue_name: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._queue_name = queue_name
        self._session_factory = session_factory
        self._connection: AbstractRobustConnection | None = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=1)
        # Connect to the pre-declared queue without modifying its configuration
        queue = await channel.declare_queue(self._queue_name, passive=True)
        await queue.consume(self._handle_message)
        logger.debug("consuming from queue '%s'", self._queue_name)

    async def stop(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        # Permanent failures (malformed payload) — route to DLQ immediately.
        try:
            payload: dict[str, str] = json.loads(message.body)
            recorded_at = datetime.now(UTC)
            record = _deserialise(payload, recorded_at)
        except Exception:
            logger.exception("failed to deserialise audit event, routing to DLQ")
            await message.nack(requeue=False)
            return

        # Transient failures (DB connection issues) — let the exception propagate.
        # The message stays unacked; aio-pika's robust connection requeues it on
        # channel recovery. ON CONFLICT DO NOTHING absorbs any duplicate on retry.
        async with self._session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyCalculationRecordRepository(session)
                await repo.save(record)

        try:
            await message.ack()
        except Exception:
            # Record is persisted. Do NOT nack — nack(requeue=False) would route
            # to DLQ despite the record already being saved.
            # Re-raise so the channel closes; RabbitMQ requeues unACK'd messages
            # on channel close (AMQP guarantee), and ON CONFLICT DO NOTHING
            # absorbs the duplicate on the next delivery attempt.
            logger.exception(
                "record persisted but ACK failed for %s; RabbitMQ will redeliver",
                record.correlation_id,
            )
            raise

        logger.debug("recorded and acked audit event %s", record.correlation_id)
