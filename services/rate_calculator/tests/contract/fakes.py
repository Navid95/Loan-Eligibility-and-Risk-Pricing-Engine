from decimal import Decimal
from uuid import uuid4

from rate_calculator.application.ports.credit_tier_config_repository import (
    CreditTierConfigRepository,
)
from rate_calculator.application.ports.district_risk_config_repository import (
    DistrictRiskConfigRepository,
)
from rate_calculator.application.ports.outbox_repository import OutboxRepository
from rate_calculator.application.ports.postal_code_mapping_repository import (
    PostalCodeMappingRepository,
)
from rate_calculator.application.ports.system_rate_config_repository import (
    SystemRateConfigRepository,
)
from rate_calculator.domain.aggregates import (
    CreditTierConfig,
    DistrictRiskConfig,
    SystemRateConfig,
)
from rate_calculator.domain.entities import PostalCodeMapping
from rate_calculator.domain.events import RateCalculated
from rate_calculator.domain.value_objects import (
    CreditTier,
    District,
    Multiplier,
    PostalCode,
    Rate,
)


class FakeSystemRateConfigRepository(SystemRateConfigRepository):
    def __init__(self, base_rate: Decimal = Decimal("5.0")) -> None:
        self._config = SystemRateConfig(id=uuid4(), base_rate=Rate(base_rate))

    async def get(self) -> SystemRateConfig:
        return self._config

    async def save(self, config: SystemRateConfig) -> None:
        self._config = config


class FakeCreditTierConfigRepository(CreditTierConfigRepository):
    def __init__(self) -> None:
        self._store: dict[str, CreditTierConfig] = {}

    def seed(self, tier: str, multiplier: Decimal) -> None:
        self._store[tier] = CreditTierConfig(
            tier=CreditTier(tier), multiplier=Multiplier(multiplier)
        )

    async def get(self, tier: CreditTier) -> CreditTierConfig | None:
        return self._store.get(tier.value)

    async def list_all(self) -> list[CreditTierConfig]:
        return list(self._store.values())

    async def save(self, config: CreditTierConfig) -> None:
        self._store[config.tier.value] = config


class FakeDistrictRiskConfigRepository(DistrictRiskConfigRepository):
    def __init__(self) -> None:
        self._store: dict[str, DistrictRiskConfig] = {}
        self._region2: dict[str, str] = {}

    def seed(self, district: str, multiplier: Decimal, region2: str = "") -> None:
        self._store[district] = DistrictRiskConfig(
            district=District(district), multiplier=Multiplier(multiplier)
        )
        self._region2[district] = region2

    async def get(self, district: District) -> DistrictRiskConfig | None:
        return self._store.get(district.name)

    async def list_all(
        self, *, page: int, page_size: int
    ) -> tuple[list[DistrictRiskConfig], int]:
        all_configs = list(self._store.values())
        total = len(all_configs)
        start = (page - 1) * page_size
        return all_configs[start : start + page_size], total

    async def list_by_region2(self, region2: str) -> list[DistrictRiskConfig]:
        return [
            config
            for name, config in self._store.items()
            if self._region2.get(name) == region2
        ]

    async def save(self, config: DistrictRiskConfig) -> None:
        self._store[config.district.name] = config

    async def save_many(self, configs: list[DistrictRiskConfig]) -> None:
        for config in configs:
            await self.save(config)


class FakePostalCodeMappingRepository(PostalCodeMappingRepository):
    def __init__(self) -> None:
        self._store: dict[str, PostalCodeMapping] = {}

    def seed(
        self,
        postal_code: str,
        district: str,
        region1: str = "",
        region2: str = "",
        region3: str = "",
    ) -> None:
        self._store[postal_code] = PostalCodeMapping(
            postal_code=PostalCode(postal_code),
            district=District(district),
            region1=region1,
            region2=region2,
            region3=region3,
        )

    async def get(self, postal_code: PostalCode) -> PostalCodeMapping | None:
        return self._store.get(postal_code.value)


class FakeOutboxRepository(OutboxRepository):
    def __init__(self) -> None:
        self.saved: list[RateCalculated] = []

    async def save(self, event: RateCalculated) -> None:
        self.saved.append(event)
