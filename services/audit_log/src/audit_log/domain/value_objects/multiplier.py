from dataclasses import dataclass
from decimal import Decimal

from audit_log.domain.exceptions import DomainError


@dataclass(frozen=True)
class Multiplier:
    value: Decimal

    def __post_init__(self) -> None:
        self._validate_value()

    def _validate_value(self) -> None:
        if self.value <= 0:
            raise DomainError(
                context={"value": str(self.value), "reason": "must be greater than 0"}
            )
