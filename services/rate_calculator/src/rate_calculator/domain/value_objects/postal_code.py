import re
from dataclasses import dataclass

from rate_calculator.domain.exceptions import DomainError

_POSTCODE_RE = re.compile(r"^\d{5}$")


@dataclass(frozen=True)
class PostalCode:
    value: str

    def __post_init__(self) -> None:
        self.validate_value()

    def validate_value(self) -> None:
        if not _POSTCODE_RE.match(self.value):
            raise DomainError(
                context={
                    "value": self.value,
                    "reason": "must be a 5-digit German postcode",
                }
            )
