import pytest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import PostalCode


class TestPostalCode:
    @pytest.mark.parametrize("value", ["12345", "00000", "99999", "01234"])
    def test_valid_postcodes_are_accepted(self, value: str) -> None:
        assert PostalCode(value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "",  # empty
            "1234",  # too short
            "123456",  # too long
            "1234A",  # contains letter
            "abcde",  # all letters
            "12 45",  # internal space
            " 12345",  # leading space
            "12345 ",  # trailing space
        ],
    )
    def test_invalid_postcodes_raise_domain_error(self, value: str) -> None:
        with pytest.raises(DomainError) as exc_info:
            PostalCode(value)
        assert "value" in exc_info.value.context

    def test_equal_postcodes_are_equal(self) -> None:
        assert PostalCode("12345") == PostalCode("12345")
