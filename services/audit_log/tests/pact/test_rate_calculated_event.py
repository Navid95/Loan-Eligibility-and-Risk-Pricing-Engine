"""
Pact consumer test for the RateCalculated event.

audit_log is the consumer — it receives RateCalculated messages from rate_calculator
via RabbitMQ. This test defines the payload shape audit_log expects and verifies
that _deserialise() can correctly process it.

The generated pact file can be used by rate_calculator to verify its serialiser
produces the agreed shape (provider-side verification).
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate
from audit_log.infrastructure.messaging.consumer import _deserialise
from pact import Consumer, MessagePact, Provider

# pact-python's Ruby binary cannot handle paths with spaces
PACT_DIR = Path("/tmp/pacts/audit_log")
PACT_DIR.mkdir(parents=True, exist_ok=True)

_CORRELATION_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
_CALCULATED_AT = datetime(2026, 5, 18, 10, 0, 0, tzinfo=UTC)

# The agreed payload shape — must match what rate_calculator's outbox publishes.
EXPECTED_PAYLOAD: dict[str, str] = {
    "correlation_id": str(_CORRELATION_ID),
    "credit_tier": "A",
    "district": "Breisgau-Hochschwarzwald",
    "base_rate": "5.000000",
    "term_multiplier": "1.300000",
    "credit_tier_multiplier": "0.950000",
    "regional_risk_multiplier": "1.100000",
    "final_rate": "6.786500",
    "calculated_at": _CALCULATED_AT.isoformat(),
}


def test_consumer_can_deserialise_rate_calculated_event() -> None:
    """
    Consumer contract: defines what audit_log expects on the queue and verifies
    that _deserialise() reconstructs the correct domain aggregate from that payload.
    Writes the pact file to PACT_DIR for provider-side verification by rate_calculator.
    """
    pact = MessagePact(
        Consumer("audit_log"),
        Provider("rate_calculator"),
        pact_dir=str(PACT_DIR),
    )

    (
        pact.given("a loan rate has been calculated")
        .expects_to_receive("a RateCalculated event")
        .with_content(EXPECTED_PAYLOAD)
        .with_metadata({"content-type": "application/json"})
    )

    recorded_at = datetime(2026, 5, 18, 10, 0, 1, tzinfo=UTC)
    record = _deserialise(EXPECTED_PAYLOAD, recorded_at)

    assert isinstance(record, CalculationRecord)
    assert record.correlation_id == _CORRELATION_ID
    assert record.credit_tier == CreditTier.A
    assert record.district == District("Breisgau-Hochschwarzwald")
    assert record.base_rate == Rate(Decimal("5.000000"))
    assert record.term_multiplier == Multiplier(Decimal("1.300000"))
    assert record.credit_tier_multiplier == Multiplier(Decimal("0.950000"))
    assert record.regional_risk_multiplier == Multiplier(Decimal("1.100000"))
    assert record.final_rate == Rate(Decimal("6.786500"))
    assert record.calculated_at == _CALCULATED_AT
    assert record.recorded_at == recorded_at

    with pact:
        pass  # triggers write_to_pact_file on __exit__
