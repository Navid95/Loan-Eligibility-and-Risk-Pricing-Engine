from dataclasses import dataclass

from rate_calculator.domain.exceptions import DomainError


@dataclass(frozen=True)
class District:
    name: str

    def __post_init__(self) -> None:
        self.validate_name()

    def validate_name(self) -> None:
        if not self.name.strip():
            raise DomainError(
                context={"name": self.name, "reason": "must not be empty or whitespace"}
            )
