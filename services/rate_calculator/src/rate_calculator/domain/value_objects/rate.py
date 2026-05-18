from dataclasses import dataclass
from decimal import Decimal

from rate_calculator.domain.exceptions import DomainError


@dataclass(frozen=True)
class Rate:
    value: Decimal

    def __post_init__(self) -> None:
        self.validate_value()

    def validate_value(self) -> None:
        if self.value <= 0:
            raise DomainError(
                context={"value": str(self.value), "reason": "must be greater than 0"}
            )
