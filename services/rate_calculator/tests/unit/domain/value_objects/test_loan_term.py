from decimal import Decimal

import pytest
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import LoanTerm


class TestLoanTerm:
    @pytest.mark.parametrize("months", [1, 12, 13, 36, 37, 60, 61, 120])
    def test_valid_months_are_accepted(self, months: int) -> None:
        assert LoanTerm(months).months == months

    @pytest.mark.parametrize("months", [0, -1, -12])
    def test_non_positive_months_raise_domain_error(self, months: int) -> None:
        with pytest.raises(DomainError) as exc_info:
            LoanTerm(months)
        assert "months" in exc_info.value.context

    # Boundary tests are critical for financial calculations — each breakpoint
    # must be verified at both edges to prevent off-by-one mispricing.
    @pytest.mark.parametrize(
        ("months", "expected"),
        [
            (1, Decimal("0.8")),  # lower bound of ≤12 bracket
            (12, Decimal("0.8")),  # upper bound of ≤12 bracket
            (13, Decimal("1.0")),  # lower bound of 13–36 bracket
            (36, Decimal("1.0")),  # upper bound of 13–36 bracket
            (37, Decimal("1.3")),  # lower bound of 37–60 bracket
            (60, Decimal("1.3")),  # upper bound of 37–60 bracket
            (61, Decimal("1.7")),  # lower bound of >60 bracket
            (120, Decimal("1.7")),
        ],
    )
    def test_term_multiplier_returns_correct_value(
        self, months: int, expected: Decimal
    ) -> None:
        assert LoanTerm(months).term_multiplier() == expected

    def test_equal_loan_terms_are_equal(self) -> None:
        assert LoanTerm(12) == LoanTerm(12)
