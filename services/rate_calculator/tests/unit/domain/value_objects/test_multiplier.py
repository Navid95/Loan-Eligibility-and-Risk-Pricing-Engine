from decimal import Decimal

import pytest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import Multiplier


class TestMultiplier:
    @pytest.mark.parametrize("value", ["0.01", "1.0", "1.3", "99.99"])
    def test_valid_values_are_accepted(self, value: str) -> None:
        assert Multiplier(Decimal(value)).value == Decimal(value)

    @pytest.mark.parametrize("value", ["0", "-0.01", "-1.0"])
    def test_non_positive_values_raise_domain_error(self, value: str) -> None:
        with pytest.raises(DomainError) as exc_info:
            Multiplier(Decimal(value))
        assert "value" in exc_info.value.context

    def test_equal_multipliers_are_equal(self) -> None:
        assert Multiplier(Decimal("1.3")) == Multiplier(Decimal("1.3"))
