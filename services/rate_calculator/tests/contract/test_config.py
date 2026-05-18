from decimal import Decimal

from fastapi.testclient import TestClient

from tests.contract.fakes import (
    FakeCreditTierConfigRepository,
    FakeDistrictRiskConfigRepository,
)


class TestSystemConfigEndpoints:
    def test_get_system_config_returns_200_with_base_rate(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/v1/config/system")

        assert response.status_code == 200
        assert "base_rate" in response.json()

    def test_update_base_rate_returns_200_with_updated_value(
        self,
        client: TestClient,
    ) -> None:
        response = client.put("/api/v1/config/system", json={"base_rate": "7.500000"})

        assert response.status_code == 200
        assert Decimal(response.json()["base_rate"]) == Decimal("7.5")

    def test_update_base_rate_persists_new_value(
        self,
        client: TestClient,
    ) -> None:
        client.put("/api/v1/config/system", json={"base_rate": "6.25"})
        response = client.get("/api/v1/config/system")

        assert Decimal(response.json()["base_rate"]) == Decimal("6.25")


class TestCreditTierEndpoints:
    def test_list_credit_tiers_returns_empty_list_when_none_configured(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/v1/config/credit-tiers")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_credit_tiers_returns_all_configured_tiers(
        self,
        client: TestClient,
        credit_tier_repo: FakeCreditTierConfigRepository,
    ) -> None:
        credit_tier_repo.seed("A", Decimal("0.9"))
        credit_tier_repo.seed("B", Decimal("1.0"))

        response = client.get("/api/v1/config/credit-tiers")

        assert response.status_code == 200
        tiers = {item["tier"]: item for item in response.json()}
        assert "A" in tiers
        assert "B" in tiers

    def test_create_credit_tier_returns_201(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/config/credit-tiers",
            json={"tier": "A", "multiplier": "0.95"},
        )

        assert response.status_code == 201
        assert response.json()["tier"] == "A"
        assert Decimal(response.json()["multiplier"]) == Decimal("0.95")

    def test_create_duplicate_credit_tier_returns_409(
        self,
        client: TestClient,
    ) -> None:
        client.post(
            "/api/v1/config/credit-tiers", json={"tier": "A", "multiplier": "0.95"}
        )
        response = client.post(
            "/api/v1/config/credit-tiers", json={"tier": "A", "multiplier": "1.0"}
        )

        assert response.status_code == 409

    def test_create_invalid_credit_tier_returns_422(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/config/credit-tiers", json={"tier": "X", "multiplier": "1.0"}
        )

        assert response.status_code == 422

    def test_update_credit_tier_multiplier_returns_200(
        self,
        client: TestClient,
        credit_tier_repo: FakeCreditTierConfigRepository,
    ) -> None:
        credit_tier_repo.seed("B", Decimal("1.0"))

        response = client.put(
            "/api/v1/config/credit-tiers/B", json={"multiplier": "1.15"}
        )

        assert response.status_code == 200
        assert response.json()["tier"] == "B"
        assert Decimal(response.json()["multiplier"]) == Decimal("1.15")

    def test_update_nonexistent_credit_tier_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.put(
            "/api/v1/config/credit-tiers/A", json={"multiplier": "1.1"}
        )

        assert response.status_code == 404

    def test_update_invalid_credit_tier_string_returns_422(
        self,
        client: TestClient,
    ) -> None:
        response = client.put(
            "/api/v1/config/credit-tiers/X", json={"multiplier": "1.1"}
        )

        assert response.status_code == 422


class TestDistrictRiskEndpoints:
    def test_list_districts_returns_empty_page_when_none_configured(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/v1/config/districts")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_list_districts_returns_all_items_with_correct_total(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        for i in range(5):
            district_repo.seed(f"District{i}", Decimal("1.0"))

        response = client.get("/api/v1/config/districts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_list_districts_paginates_correctly(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        for i in range(5):
            district_repo.seed(f"District{i}", Decimal("1.0"))

        response = client.get("/api/v1/config/districts?page=2&page_size=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 2
        assert data["page_size"] == 3

    def test_get_district_returns_200_with_correct_multiplier(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        district_repo.seed("Mitte", Decimal("1.25"))

        response = client.get("/api/v1/config/districts/Mitte")

        assert response.status_code == 200
        assert response.json()["district"] == "Mitte"
        assert Decimal(response.json()["multiplier"]) == Decimal("1.25")

    def test_get_unknown_district_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/api/v1/config/districts/UnknownDistrict")

        assert response.status_code == 404

    def test_update_district_risk_index_returns_200(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        district_repo.seed("Mitte", Decimal("1.0"))

        response = client.put(
            "/api/v1/config/districts/Mitte", json={"multiplier": "1.5"}
        )

        assert response.status_code == 200
        assert Decimal(response.json()["multiplier"]) == Decimal("1.5")

    def test_update_nonexistent_district_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.put(
            "/api/v1/config/districts/UnknownDistrict", json={"multiplier": "1.5"}
        )

        assert response.status_code == 404


class TestRegionBulkUpdateEndpoint:
    def test_bulk_update_region_returns_200_with_updated_count(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        district_repo.seed("Mitte", Decimal("1.0"), region2="Berlin")
        district_repo.seed("Charlottenburg", Decimal("1.1"), region2="Berlin")

        response = client.put(
            "/api/v1/config/regions/Berlin", json={"multiplier": "1.3"}
        )

        assert response.status_code == 200
        assert response.json()["updated"] == 2

    def test_bulk_update_unknown_region_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.put(
            "/api/v1/config/regions/UnknownRegion", json={"multiplier": "1.3"}
        )

        assert response.status_code == 404

    def test_bulk_update_applies_multiplier_to_all_districts_in_region(
        self,
        client: TestClient,
        district_repo: FakeDistrictRiskConfigRepository,
    ) -> None:
        district_repo.seed("Mitte", Decimal("1.0"), region2="Berlin")
        district_repo.seed("Charlottenburg", Decimal("1.1"), region2="Berlin")
        district_repo.seed("München-Stadt", Decimal("1.2"), region2="Oberbayern")

        client.put("/api/v1/config/regions/Berlin", json={"multiplier": "1.5"})

        mitte = client.get("/api/v1/config/districts/Mitte").json()
        charlottenburg = client.get("/api/v1/config/districts/Charlottenburg").json()
        muenchen = client.get("/api/v1/config/districts/München-Stadt").json()

        assert Decimal(mitte["multiplier"]) == Decimal("1.5")
        assert Decimal(charlottenburg["multiplier"]) == Decimal("1.5")
        assert Decimal(muenchen["multiplier"]) == Decimal("1.2")
