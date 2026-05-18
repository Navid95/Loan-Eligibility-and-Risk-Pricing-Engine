from uuid import UUID

from rate_calculator.domain.value_objects import Rate


class SystemRateConfig:
    def __init__(self, *, id: UUID, base_rate: Rate) -> None:
        self._id = id
        self._base_rate = base_rate

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def base_rate(self) -> Rate:
        return self._base_rate

    def update_base_rate(self, new_rate: Rate) -> None:
        self._base_rate = new_rate
