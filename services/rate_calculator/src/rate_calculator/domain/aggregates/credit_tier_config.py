from rate_calculator.domain.value_objects import CreditTier, Multiplier


class CreditTierConfig:
    def __init__(self, *, tier: CreditTier, multiplier: Multiplier) -> None:
        self._tier = tier
        self._multiplier = multiplier

    @property
    def tier(self) -> CreditTier:
        return self._tier

    @property
    def multiplier(self) -> Multiplier:
        return self._multiplier

    def update_multiplier(self, new_multiplier: Multiplier) -> None:
        self._multiplier = new_multiplier
