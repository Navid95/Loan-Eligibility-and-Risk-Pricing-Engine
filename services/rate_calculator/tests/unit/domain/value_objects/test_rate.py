from decimal import Decimal

import pytest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import Rate


class TestRate:
    @pytest.mark.parametrize("value", ["0.01", "5.0", "100.0"])
    def test_valid_values_are_accepted(self, value: str) -> None:
        assert Rate(Decimal(value)).value == Decimal(value)

    @pytest.mark.parametrize("value", ["0", "-0.01", "-5.0"])
    def test_non_positive_values_raise_domain_error(self, value: str) -> None:
        with pytest.raises(DomainError) as exc_info:
            Rate(Decimal(value))
        assert "value" in exc_info.value.context

    def test_equal_rates_are_equal(self) -> None:
        assert Rate(Decimal("5.0")) == Rate(Decimal("5.0"))
