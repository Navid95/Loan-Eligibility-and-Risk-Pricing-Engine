from rate_calculator.domain.value_objects import District, Multiplier


class DistrictRiskConfig:
    def __init__(self, *, district: District, multiplier: Multiplier) -> None:
        self._district = district
        self._multiplier = multiplier

    @property
    def district(self) -> District:
        return self._district

    @property
    def multiplier(self) -> Multiplier:
        return self._multiplier

    def update_risk_index(self, new_multiplier: Multiplier) -> None:
        self._multiplier = new_multiplier
