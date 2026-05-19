from decimal import Decimal

import httpx


class TestConfigEndpoints:
    # -------------------------------------------------------------------------
    # System config
    # -------------------------------------------------------------------------

    def test_get_system_config_returns_base_rate(
        self, admin_client: httpx.Client
    ) -> None:
        response = admin_client.get("/api/v1/config/system")

        assert response.status_code == 200
        assert "base_rate" in response.json()

    def test_update_base_rate_is_reflected_in_calculation(
        self, admin_client: httpx.Client, broker_client: httpx.Client
    ) -> None:
        admin_client.put("/api/v1/config/system", json={"base_rate": "2.0"})
        try:
            response = broker_client.post(
                "/api/v1/rates/calculate",
                json={
                    "postal_code": "79100",
                    "loan_term_months": 12,
                    "credit_tier": "A",
                },
            )
            assert response.status_code == 200
            assert Decimal(response.json()["base_rate"]) == Decimal("2.0")
        finally:
            admin_client.put("/api/v1/config/system", json={"base_rate": "1.03"})

    # -------------------------------------------------------------------------
    # Credit tier config
    # -------------------------------------------------------------------------

    def test_list_credit_tiers_returns_seeded_tiers(
        self, admin_client: httpx.Client
    ) -> None:
        response = admin_client.get("/api/v1/config/credit-tiers")

        assert response.status_code == 200
        tiers = {item["tier"] for item in response.json()}
        assert {"A", "B", "C"} <= tiers

    def test_create_duplicate_credit_tier_returns_409(
        self, admin_client: httpx.Client
    ) -> None:
        response = admin_client.post(
            "/api/v1/config/credit-tiers",
            json={"tier": "A", "multiplier": "1.05"},
        )

        assert response.status_code == 409

    def test_update_credit_tier_multiplier(self, admin_client: httpx.Client) -> None:
        admin_client.put("/api/v1/config/credit-tiers/A", json={"multiplier": "0.90"})
        try:
            response = admin_client.get("/api/v1/config/credit-tiers")
            tiers = {item["tier"]: item["multiplier"] for item in response.json()}
            assert Decimal(tiers["A"]) == Decimal("0.90")
        finally:
            admin_client.put(
                "/api/v1/config/credit-tiers/A", json={"multiplier": "1.05"}
            )

    # -------------------------------------------------------------------------
    # District risk config
    # -------------------------------------------------------------------------

    def test_list_districts_returns_paginated_results(
        self, admin_client: httpx.Client
    ) -> None:
        response = admin_client.get("/api/v1/config/districts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["items"]) > 0
        assert "page" in data
        assert "page_size" in data

    def test_get_district_returns_multiplier(self, admin_client: httpx.Client) -> None:
        response = admin_client.get("/api/v1/config/districts/München")

        assert response.status_code == 200
        assert "multiplier" in response.json()

    def test_update_district_risk_index_is_reflected_in_calculation(
        self, admin_client: httpx.Client, broker_client: httpx.Client
    ) -> None:
        # 79189 resolves to Breisgau-Hochschwarzwald in the seeded CSV data
        district = "Breisgau-Hochschwarzwald"
        admin_client.put(
            f"/api/v1/config/districts/{district}", json={"multiplier": "1.5"}
        )
        try:
            response = broker_client.post(
                "/api/v1/rates/calculate",
                json={
                    "postal_code": "79189",
                    "loan_term_months": 12,
                    "credit_tier": "A",
                },
            )
            assert response.status_code == 200
            assert Decimal(response.json()["regional_risk_multiplier"]) == Decimal(
                "1.5"
            )
        finally:
            admin_client.put(
                f"/api/v1/config/districts/{district}", json={"multiplier": "1.0"}
            )

    def test_bulk_update_region_returns_updated_count(
        self, admin_client: httpx.Client
    ) -> None:
        response = admin_client.put(
            "/api/v1/config/regions/Freiburg", json={"multiplier": "1.1"}
        )
        try:
            assert response.status_code == 200
            assert response.json()["updated"] > 0
        finally:
            admin_client.put(
                "/api/v1/config/regions/Freiburg", json={"multiplier": "1.0"}
            )
