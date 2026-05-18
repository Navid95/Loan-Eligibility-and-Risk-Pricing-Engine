import pytest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import District


class TestDistrict:
    @pytest.mark.parametrize("name", ["München", "Stuttgart", "Freiburg im Breisgau"])
    def test_valid_names_are_accepted(self, name: str) -> None:
        assert District(name).name == name

    @pytest.mark.parametrize("name", ["", "   ", "\t"])
    def test_empty_or_whitespace_names_raise_domain_error(self, name: str) -> None:
        with pytest.raises(DomainError) as exc_info:
            District(name)
        assert "name" in exc_info.value.context

    def test_equal_districts_are_equal(self) -> None:
        assert District("München") == District("München")
