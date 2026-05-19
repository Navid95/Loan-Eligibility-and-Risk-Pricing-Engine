from dataclasses import dataclass

from audit_log.domain.exceptions import DomainError


@dataclass(frozen=True)
class District:
    name: str

    def __post_init__(self) -> None:
        self._validate_name()

    def _validate_name(self) -> None:
        if not self.name.strip():
            raise DomainError(
                context={"name": self.name, "reason": "must not be empty or whitespace"}
            )
