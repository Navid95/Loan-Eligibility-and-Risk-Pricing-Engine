from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.domain.exceptions import DomainError


@dataclass(frozen=True)
class LoanTerm:
    months: int

    def __post_init__(self) -> None:
        self.validate_months()

    def validate_months(self) -> None:
        if self.months <= 0:
            raise DomainError(
                context={"months": self.months, "reason": "must be greater than 0"}
            )

    def term_multiplier(self) -> Decimal:
        if self.months <= 12:
            return Decimal("0.8")
        if self.months <= 36:
            return Decimal("1.0")
        if self.months <= 60:
            return Decimal("1.3")
        return Decimal("1.7")
