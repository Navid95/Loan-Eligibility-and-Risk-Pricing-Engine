from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate


@pytest.fixture
def record() -> CalculationRecord:
    return CalculationRecord(
        correlation_id=uuid4(),
        credit_tier=CreditTier.A,
        district=District("München"),
        base_rate=Rate(Decimal("1.03")),
        term_multiplier=Multiplier(Decimal("1.0")),
        credit_tier_multiplier=Multiplier(Decimal("1.05")),
        regional_risk_multiplier=Multiplier(Decimal("1.0")),
        final_rate=Rate(Decimal("1.0815")),
        calculated_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 5, 19, 10, 0, 1, tzinfo=UTC),
    )


class TestCalculationRecord:
    def test_properties_reflect_construction_values(
        self, record: CalculationRecord
    ) -> None:
        assert record.credit_tier == CreditTier.A
        assert record.district == District("München")
        assert record.base_rate == Rate(Decimal("1.03"))
        assert record.term_multiplier == Multiplier(Decimal("1.0"))
        assert record.credit_tier_multiplier == Multiplier(Decimal("1.05"))
        assert record.regional_risk_multiplier == Multiplier(Decimal("1.0"))
        assert record.final_rate == Rate(Decimal("1.0815"))
        assert record.calculated_at == datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)
        assert record.recorded_at == datetime(2026, 5, 19, 10, 0, 1, tzinfo=UTC)

    def test_correlation_id_is_preserved(self) -> None:
        cid = uuid4()
        record = CalculationRecord(
            correlation_id=cid,
            credit_tier=CreditTier.B,
            district=District("Stuttgart"),
            base_rate=Rate(Decimal("1.03")),
            term_multiplier=Multiplier(Decimal("1.3")),
            credit_tier_multiplier=Multiplier(Decimal("1.0")),
            regional_risk_multiplier=Multiplier(Decimal("1.0")),
            final_rate=Rate(Decimal("1.339")),
            calculated_at=datetime.now(UTC),
            recorded_at=datetime.now(UTC),
        )
        assert record.correlation_id == cid
