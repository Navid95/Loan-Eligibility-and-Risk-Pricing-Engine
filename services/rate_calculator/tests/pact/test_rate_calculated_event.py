"""
Message Pact tests for the RateCalculated event.

Consumer: audit_log — expects a fixed JSON payload shape on the queue.
Provider: rate_calculator — serialises RateCalculated domain events via the
outbox repository before they are published to RabbitMQ.

Structure:
  test_consumer_can_process_rate_calculated_event
    → defines the consumer contract; generates pacts/audit_log-rate_calculator.json
  test_provider_serialises_event_matching_consumer_contract
    → verifies the actual serialiser output matches the agreed shape
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from pact import Consumer, MessagePact, Provider
from rate_calculator.domain.events.rate_calculated import RateCalculated
from rate_calculator.domain.value_objects import CreditTier, District, Multiplier, Rate
from rate_calculator.infrastructure.repositories.outbox_repository import _serialise

# pact-python's Ruby binary cannot handle paths with spaces, so pact files are
# written to /tmp/pacts rather than next to the test file.
PACT_DIR = Path("/tmp/pacts/rate_calculator")
PACT_DIR.mkdir(parents=True, exist_ok=True)

_CORRELATION_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
_CALCULATED_AT = datetime(2026, 5, 18, 10, 0, 0, tzinfo=UTC)

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


def _build_event() -> RateCalculated:
    return RateCalculated(
        correlation_id=_CORRELATION_ID,
        credit_tier=CreditTier.A,
        district=District("Breisgau-Hochschwarzwald"),
        base_rate=Rate(Decimal("5.000000")),
        term_multiplier=Multiplier(Decimal("1.300000")),
        credit_tier_multiplier=Multiplier(Decimal("0.950000")),
        regional_risk_multiplier=Multiplier(Decimal("1.100000")),
        final_rate=Rate(Decimal("6.786500")),
        calculated_at=_CALCULATED_AT,
    )


def test_consumer_can_process_rate_calculated_event() -> None:
    """Consumer side: audit_log defines what it expects on the queue."""
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

    def audit_log_handler(body: dict) -> None:
        # audit_log must be able to read all fields it depends on
        assert "correlation_id" in body
        assert "credit_tier" in body
        assert "district" in body
        assert "final_rate" in body
        assert "calculated_at" in body

    # Call handler directly with expected content, then write the pact file.
    # MessagePact in pact-python v2 does not have a verify() method — consumer
    # tests invoke the handler with the agreed payload and rely on the context
    # manager to flush the pact JSON to disk.
    audit_log_handler(EXPECTED_PAYLOAD)
    with pact:
        pass  # triggers write_to_pact_file on __exit__


def test_provider_serialises_event_matching_consumer_contract() -> None:
    """Provider side: rate_calculator's serialiser must produce the agreed shape."""
    actual = _serialise(_build_event())
    assert actual == EXPECTED_PAYLOAD
