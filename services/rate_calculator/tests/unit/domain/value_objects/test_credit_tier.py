import pytest
from rate_calculator.domain.value_objects import CreditTier


class TestCreditTier:
    @pytest.mark.parametrize("value", ["A", "B", "C"])
    def test_valid_tiers_are_accepted(self, value: str) -> None:
        assert CreditTier(value) == value

    @pytest.mark.parametrize("value", ["D", "a", "b", "c", "", "AA"])
    def test_invalid_tiers_raise_value_error(self, value: str) -> None:
        with pytest.raises(ValueError):
            CreditTier(value)

    def test_equal_tiers_are_equal(self) -> None:
        assert CreditTier("A") == CreditTier("A")
