from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.contract.fakes import (
    FakeCreditTierConfigRepository,
    FakeDistrictRiskConfigRepository,
    FakeOutboxRepository,
    FakePostalCodeMappingRepository,
)


class TestRatesEndpoint:
    def test_calculate_rate_returns_200_with_full_breakdown(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
        credit_tier_repo: FakeCreditTierConfigRepository,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        postal_code_repo.seed("79100", "Breisgau-Hochschwarzwald", region2="Freiburg")
        credit_tier_repo.seed("A", Decimal("0.95"))
        district_repo.seed("Breisgau-Hochschwarzwald", Decimal("1.10"))

        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 48, "credit_tier": "A"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["credit_tier"] == "A"
        assert data["district"] == "Breisgau-Hochschwarzwald"
        assert Decimal(data["base_rate"]) == Decimal("5.0")
        assert Decimal(data["term_multiplier"]) == Decimal("1.3")
        assert Decimal(data["credit_tier_multiplier"]) == Decimal("0.95")
        assert Decimal(data["regional_risk_multiplier"]) == Decimal("1.10")
        assert "final_rate" in data
        assert "correlation_id" in data
        assert "calculated_at" in data

    def test_calculate_rate_correlation_id_is_echoed_from_header(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
        credit_tier_repo: FakeCreditTierConfigRepository,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        postal_code_repo.seed("80331", "München")
        credit_tier_repo.seed("B", Decimal("1.0"))
        district_repo.seed("München", Decimal("1.0"))
        correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "80331", "loan_term_months": 24, "credit_tier": "B"},
            headers={"X-Correlation-Id": correlation_id},
        )

        assert response.status_code == 200
        assert response.json()["correlation_id"] == correlation_id

    def test_calculate_rate_missing_correlation_id_header_returns_422(
        self,
        client: TestClient,
    ) -> None:
        del client.headers["X-Correlation-Id"]
        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "80331", "loan_term_months": 12, "credit_tier": "C"},
        )

        assert response.status_code == 422

    def test_calculate_rate_unknown_postal_code_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "99999", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 404
        assert "99999" in response.json()["detail"]

    def test_calculate_rate_invalid_postal_code_format_returns_422(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "ABCDE", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 422

    def test_calculate_rate_unknown_credit_tier_returns_422(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 12, "credit_tier": "X"},
        )

        assert response.status_code == 422

    def test_calculate_rate_missing_credit_tier_config_returns_404(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
    ) -> None:
        postal_code_repo.seed("79100", "Breisgau-Hochschwarzwald")

        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 404

    def test_calculate_rate_missing_district_config_returns_404(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
        credit_tier_repo: FakeCreditTierConfigRepository,
    ) -> None:
        postal_code_repo.seed("79100", "Breisgau-Hochschwarzwald")
        credit_tier_repo.seed("A", Decimal("0.95"))

        response = client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 404

    def test_calculate_rate_saves_event_to_outbox(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
        credit_tier_repo: FakeCreditTierConfigRepository,
        district_repo: FakeDistrictRiskConfigRepository,
        outbox_repo: FakeOutboxRepository,
    ) -> None:
        postal_code_repo.seed("79100", "Breisgau-Hochschwarzwald")
        credit_tier_repo.seed("A", Decimal("0.95"))
        district_repo.seed("Breisgau-Hochschwarzwald", Decimal("1.10"))

        client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 24, "credit_tier": "A"},
        )

        assert len(outbox_repo.saved) == 1
        event = outbox_repo.saved[0]
        assert event.credit_tier.value == "A"
        assert event.district.name == "Breisgau-Hochschwarzwald"

    @pytest.mark.parametrize(
        "loan_term_months, expected_multiplier",
        [
            (12, "0.8"),
            (24, "1.0"),
            (48, "1.3"),
            (72, "1.7"),
        ],
    )
    def test_calculate_rate_applies_correct_term_multiplier(
        self,
        client: TestClient,
        postal_code_repo: FakePostalCodeMappingRepository,
        credit_tier_repo: FakeCreditTierConfigRepository,
        district_repo: FakeDistrictRiskConfigRepository,
        loan_term_months: int,
        expected_multiplier: str,
    ) -> None:
        postal_code_repo.seed("80331", "München")
        credit_tier_repo.seed("A", Decimal("1.0"))
        district_repo.seed("München", Decimal("1.0"))

        response = client.post(
            "/api/v1/rates/calculate",
            json={
                "postal_code": "80331",
                "loan_term_months": loan_term_months,
                "credit_tier": "A",
            },
        )

        assert response.status_code == 200
        assert Decimal(response.json()["term_multiplier"]) == Decimal(
            expected_multiplier
        )
