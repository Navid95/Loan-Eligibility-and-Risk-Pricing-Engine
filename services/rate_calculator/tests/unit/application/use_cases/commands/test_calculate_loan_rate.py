from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from rate_calculator.application.exceptions import NotFoundError, ValidationError
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
from rate_calculator.application.use_cases.commands.calculate_loan_rate import (
    CalculateLoanRateCommand,
    CalculateLoanRateUseCase,
)
from rate_calculator.domain.aggregates import (
    CreditTierConfig,
    DistrictRiskConfig,
    SystemRateConfig,
)
from rate_calculator.domain.entities import PostalCodeMapping
from rate_calculator.domain.exceptions import DomainError
from rate_calculator.domain.value_objects import (
    CreditTier,
    District,
    Multiplier,
    PostalCode,
    Rate,
)


@pytest.fixture
def postal_code_mapping_repo() -> AsyncMock:
    return AsyncMock(spec=PostalCodeMappingRepository)


@pytest.fixture
def system_rate_config_repo() -> AsyncMock:
    return AsyncMock(spec=SystemRateConfigRepository)


@pytest.fixture
def credit_tier_config_repo() -> AsyncMock:
    return AsyncMock(spec=CreditTierConfigRepository)


@pytest.fixture
def district_risk_config_repo() -> AsyncMock:
    return AsyncMock(spec=DistrictRiskConfigRepository)


@pytest.fixture
def outbox_repo() -> AsyncMock:
    return AsyncMock(spec=OutboxRepository)


@pytest.fixture
def use_case(
    postal_code_mapping_repo: AsyncMock,
    system_rate_config_repo: AsyncMock,
    credit_tier_config_repo: AsyncMock,
    district_risk_config_repo: AsyncMock,
    outbox_repo: AsyncMock,
) -> CalculateLoanRateUseCase:
    return CalculateLoanRateUseCase(
        postal_code_mapping_repo=postal_code_mapping_repo,
        system_rate_config_repo=system_rate_config_repo,
        credit_tier_config_repo=credit_tier_config_repo,
        district_risk_config_repo=district_risk_config_repo,
        outbox_repo=outbox_repo,
    )


def _setup_happy_path(
    postal_code_mapping_repo: AsyncMock,
    system_rate_config_repo: AsyncMock,
    credit_tier_config_repo: AsyncMock,
    district_risk_config_repo: AsyncMock,
) -> None:
    district = District("München")
    postal_code_mapping_repo.get.return_value = PostalCodeMapping(
        postal_code=PostalCode("80331"),
        district=district,
        region1="Bayern",
        region2="Oberbayern",
        region3="München",
    )
    system_rate_config_repo.get.return_value = SystemRateConfig(
        id=uuid4(), base_rate=Rate(Decimal("5.0"))
    )
    credit_tier_config_repo.get.return_value = CreditTierConfig(
        tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
    )
    district_risk_config_repo.get.return_value = DistrictRiskConfig(
        district=district, multiplier=Multiplier(Decimal("1.1"))
    )


class TestCalculateLoanRateUseCase:
    async def test_returns_correct_final_rate(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            postal_code_mapping_repo,
            system_rate_config_repo,
            credit_tier_config_repo,
            district_risk_config_repo,
        )
        # loan term 24 months → term multiplier 1.0
        # 5.0 × 1.0 × 1.2 × 1.1 = 6.6
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="80331",
            loan_term_months=24,
            credit_tier="A",
        )
        result = await use_case.execute(command)
        assert result.final_rate == Decimal("6.6")

    async def test_result_carries_correct_breakdown(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            postal_code_mapping_repo,
            system_rate_config_repo,
            credit_tier_config_repo,
            district_risk_config_repo,
        )
        correlation_id = uuid4()
        command = CalculateLoanRateCommand(
            correlation_id=correlation_id,
            postal_code="80331",
            loan_term_months=24,
            credit_tier="A",
        )
        result = await use_case.execute(command)
        assert result.correlation_id == correlation_id
        assert result.credit_tier == "A"
        assert result.district == "München"
        assert result.base_rate == Decimal("5.0")
        assert result.term_multiplier == Decimal("1.0")
        assert result.credit_tier_multiplier == Decimal("1.2")
        assert result.regional_risk_multiplier == Decimal("1.1")
        assert result.calculated_at is not None

    @pytest.mark.parametrize(
        "loan_term_months, expected_term_multiplier",
        [
            (12, Decimal("0.8")),
            (24, Decimal("1.0")),
            (48, Decimal("1.3")),
            (72, Decimal("1.7")),
        ],
    )
    async def test_applies_correct_term_multiplier(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
        loan_term_months: int,
        expected_term_multiplier: Decimal,
    ) -> None:
        _setup_happy_path(
            postal_code_mapping_repo,
            system_rate_config_repo,
            credit_tier_config_repo,
            district_risk_config_repo,
        )
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="80331",
            loan_term_months=loan_term_months,
            credit_tier="A",
        )
        result = await use_case.execute(command)
        assert result.term_multiplier == expected_term_multiplier

    async def test_publishes_rate_calculated_event_to_outbox(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
        outbox_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            postal_code_mapping_repo,
            system_rate_config_repo,
            credit_tier_config_repo,
            district_risk_config_repo,
        )
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="80331",
            loan_term_months=24,
            credit_tier="A",
        )
        await use_case.execute(command)
        outbox_repo.save.assert_called_once()

    async def test_raises_not_found_when_postal_code_not_in_system(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        postal_code_mapping_repo.get.return_value = None
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="12345",
            loan_term_months=24,
            credit_tier="A",
        )
        with pytest.raises(NotFoundError):
            await use_case.execute(command)

    async def test_raises_not_found_when_credit_tier_config_missing(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district = District("München")
        postal_code_mapping_repo.get.return_value = PostalCodeMapping(
            postal_code=PostalCode("80331"),
            district=district,
            region1="Bayern",
            region2="Oberbayern",
            region3="München",
        )
        system_rate_config_repo.get.return_value = SystemRateConfig(
            id=uuid4(), base_rate=Rate(Decimal("5.0"))
        )
        credit_tier_config_repo.get.return_value = None
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="80331",
            loan_term_months=24,
            credit_tier="A",
        )
        with pytest.raises(NotFoundError):
            await use_case.execute(command)

    async def test_raises_not_found_when_district_risk_config_missing(
        self,
        use_case: CalculateLoanRateUseCase,
        postal_code_mapping_repo: AsyncMock,
        system_rate_config_repo: AsyncMock,
        credit_tier_config_repo: AsyncMock,
        district_risk_config_repo: AsyncMock,
    ) -> None:
        district = District("München")
        postal_code_mapping_repo.get.return_value = PostalCodeMapping(
            postal_code=PostalCode("80331"),
            district=district,
            region1="Bayern",
            region2="Oberbayern",
            region3="München",
        )
        system_rate_config_repo.get.return_value = SystemRateConfig(
            id=uuid4(), base_rate=Rate(Decimal("5.0"))
        )
        credit_tier_config_repo.get.return_value = CreditTierConfig(
            tier=CreditTier.A, multiplier=Multiplier(Decimal("1.2"))
        )
        district_risk_config_repo.get.return_value = None
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="80331",
            loan_term_months=24,
            credit_tier="A",
        )
        with pytest.raises(NotFoundError):
            await use_case.execute(command)

    async def test_raises_domain_error_for_invalid_postal_code_format(
        self, use_case: CalculateLoanRateUseCase
    ) -> None:
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="bad",
            loan_term_months=24,
            credit_tier="A",
        )
        with pytest.raises(DomainError):
            await use_case.execute(command)

    async def test_raises_domain_error_for_non_positive_loan_term(
        self, use_case: CalculateLoanRateUseCase
    ) -> None:
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="12345",
            loan_term_months=0,
            credit_tier="A",
        )
        with pytest.raises(DomainError):
            await use_case.execute(command)

    async def test_raises_validation_error_for_unknown_credit_tier(
        self, use_case: CalculateLoanRateUseCase
    ) -> None:
        command = CalculateLoanRateCommand(
            correlation_id=uuid4(),
            postal_code="12345",
            loan_term_months=24,
            credit_tier="D",
        )
        with pytest.raises(ValidationError):
            await use_case.execute(command)
