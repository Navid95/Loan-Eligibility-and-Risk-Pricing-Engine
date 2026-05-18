from decimal import Decimal
from uuid import uuid4

import pytest
from rate_calculator.domain.aggregates import CalculationRequest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import CreditTier, District, Multiplier, Rate


@pytest.fixture
def calculation_request() -> CalculationRequest:
    return CalculationRequest(
        correlation_id=uuid4(),
        credit_tier=CreditTier.A,
        district=District("München"),
        base_rate=Rate(Decimal("10.0")),
        term_multiplier=Multiplier(Decimal("1.3")),
        credit_tier_multiplier=Multiplier(Decimal("1.2")),
        regional_risk_multiplier=Multiplier(Decimal("1.5")),
    )


class TestCalculationRequestCalculate:
    def test_returns_correct_final_rate(self) -> None:
        request = CalculationRequest(
            correlation_id=uuid4(),
            credit_tier=CreditTier.A,
            district=District("München"),
            base_rate=Rate(Decimal("10.0")),
            term_multiplier=Multiplier(Decimal("1.3")),
            credit_tier_multiplier=Multiplier(Decimal("1.2")),
            regional_risk_multiplier=Multiplier(Decimal("1.5")),
        )
        # 10.0 × 1.3 × 1.2 × 1.5 = 23.4
        assert request.calculate() == Rate(Decimal("23.4"))

    def test_sets_final_rate_on_aggregate(
        self, calculation_request: CalculationRequest
    ) -> None:
        calculation_request.calculate()
        assert calculation_request.final_rate is not None

    def test_sets_calculated_at_on_aggregate(
        self, calculation_request: CalculationRequest
    ) -> None:
        calculation_request.calculate()
        assert calculation_request.calculated_at is not None

    def test_raises_domain_error_when_called_twice(
        self, calculation_request: CalculationRequest
    ) -> None:
        calculation_request.calculate()
        with pytest.raises(DomainError) as exc_info:
            calculation_request.calculate()
        assert "reason" in exc_info.value.context


class TestCalculationRequestEvents:
    def test_emits_one_event_after_calculate(
        self, calculation_request: CalculationRequest
    ) -> None:
        calculation_request.calculate()
        assert len(calculation_request.pull_events()) == 1

    def test_event_carries_correct_correlation_id(self) -> None:
        correlation_id = uuid4()
        request = CalculationRequest(
            correlation_id=correlation_id,
            credit_tier=CreditTier.A,
            district=District("München"),
            base_rate=Rate(Decimal("10.0")),
            term_multiplier=Multiplier(Decimal("1.0")),
            credit_tier_multiplier=Multiplier(Decimal("1.0")),
            regional_risk_multiplier=Multiplier(Decimal("1.0")),
        )
        request.calculate()
        assert request.pull_events()[0].correlation_id == correlation_id

    def test_event_carries_correct_final_rate(self) -> None:
        request = CalculationRequest(
            correlation_id=uuid4(),
            credit_tier=CreditTier.A,
            district=District("München"),
            base_rate=Rate(Decimal("10.0")),
            term_multiplier=Multiplier(Decimal("1.0")),
            credit_tier_multiplier=Multiplier(Decimal("1.0")),
            regional_risk_multiplier=Multiplier(Decimal("1.0")),
        )
        request.calculate()
        assert request.pull_events()[0].final_rate == Rate(Decimal("10.0"))

    def test_pull_events_clears_the_event_list(
        self, calculation_request: CalculationRequest
    ) -> None:
        calculation_request.calculate()
        calculation_request.pull_events()
        assert calculation_request.pull_events() == []
