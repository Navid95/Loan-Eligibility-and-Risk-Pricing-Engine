import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Rate
from audit_log.infrastructure.messaging.consumer import AuditEventConsumer, _deserialise
from audit_log.infrastructure.repositories.calculation_record_repository import (
    SqlAlchemyCalculationRecordRepository,
)

_RECORDED_AT = datetime(2026, 5, 19, 10, 0, 1, tzinfo=UTC)

_VALID_PAYLOAD: dict[str, str] = {
    "correlation_id": str(uuid4()),
    "credit_tier": "A",
    "district": "München",
    "base_rate": "1.030000",
    "term_multiplier": "1.000000",
    "credit_tier_multiplier": "1.050000",
    "regional_risk_multiplier": "1.000000",
    "final_rate": "1.081500",
    "calculated_at": "2026-05-19T10:00:00+00:00",
}


class TestDeserialise:
    def test_returns_calculation_record_with_correct_fields(self) -> None:
        record = _deserialise(_VALID_PAYLOAD, _RECORDED_AT)

        assert isinstance(record, CalculationRecord)
        assert record.correlation_id == UUID(_VALID_PAYLOAD["correlation_id"])
        assert record.credit_tier == CreditTier.A
        assert record.district == District("München")
        assert record.base_rate == Rate(Decimal("1.030000"))
        assert record.final_rate == Rate(Decimal("1.081500"))
        assert record.recorded_at == _RECORDED_AT

    def test_raises_for_invalid_credit_tier(self) -> None:
        payload = {**_VALID_PAYLOAD, "credit_tier": "Z"}
        with pytest.raises(ValueError):
            _deserialise(payload, _RECORDED_AT)

    def test_raises_for_missing_field(self) -> None:
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "final_rate"}
        with pytest.raises(KeyError):
            _deserialise(payload, _RECORDED_AT)

    def test_raises_for_malformed_uuid(self) -> None:
        payload = {**_VALID_PAYLOAD, "correlation_id": "not-a-uuid"}
        with pytest.raises(ValueError):
            _deserialise(payload, _RECORDED_AT)


def _make_consumer() -> tuple[AuditEventConsumer, AsyncMock, MagicMock]:
    """Return (consumer, mock_session, mock_factory)."""
    # session.begin() must be a regular call returning an async context manager,
    # not itself a coroutine.
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__ = AsyncMock(return_value=None)
    mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin_ctx)

    mock_factory = MagicMock(return_value=mock_session)
    consumer = AuditEventConsumer(
        rabbitmq_url="amqp://localhost",
        queue_name="audit.calculations",
        session_factory=mock_factory,
    )
    return consumer, mock_session, mock_factory


def _make_message(
    payload: dict | None = None, *, body: bytes | None = None
) -> MagicMock:
    msg = MagicMock()
    msg.body = (
        body if body is not None else json.dumps(payload or _VALID_PAYLOAD).encode()
    )
    msg.ack = AsyncMock()
    msg.nack = AsyncMock()
    return msg


class TestAuditEventConsumerHandleMessage:
    async def test_acks_message_after_successful_save(self) -> None:
        consumer, _, _ = _make_consumer()
        message = _make_message()

        with patch.object(
            SqlAlchemyCalculationRecordRepository, "save", new_callable=AsyncMock
        ):
            await consumer._handle_message(message)

        message.ack.assert_awaited_once()
        message.nack.assert_not_awaited()

    async def test_nacks_without_requeue_on_invalid_json(self) -> None:
        consumer, _, _ = _make_consumer()
        message = _make_message(body=b"not-json")

        await consumer._handle_message(message)

        message.nack.assert_awaited_once_with(requeue=False)
        message.ack.assert_not_awaited()

    async def test_nacks_without_requeue_on_deserialisation_error(self) -> None:
        consumer, _, _ = _make_consumer()
        message = _make_message({**_VALID_PAYLOAD, "correlation_id": "bad-uuid"})

        await consumer._handle_message(message)

        message.nack.assert_awaited_once_with(requeue=False)
        message.ack.assert_not_awaited()

    async def test_raises_on_db_error(self) -> None:
        consumer, _, _ = _make_consumer()
        message = _make_message()

        with patch.object(
            SqlAlchemyCalculationRecordRepository,
            "save",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            with pytest.raises(RuntimeError):
                await consumer._handle_message(message)

        message.nack.assert_not_awaited()
        message.ack.assert_not_awaited()

    async def test_does_not_nack_when_ack_fails(self) -> None:
        consumer, _, _ = _make_consumer()
        message = _make_message()
        message.ack = AsyncMock(side_effect=RuntimeError("broker unreachable"))

        with patch.object(
            SqlAlchemyCalculationRecordRepository, "save", new_callable=AsyncMock
        ):
            with pytest.raises(RuntimeError):
                await consumer._handle_message(message)

        message.nack.assert_not_awaited()
