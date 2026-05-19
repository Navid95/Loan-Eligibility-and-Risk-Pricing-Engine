import httpx

_VALID_RATE_PAYLOAD = {
    "postal_code": "79100",
    "loan_term_months": 12,
    "credit_tier": "A",
}


class TestAuthentication:
    def test_no_credentials_on_rates_returns_401(self) -> None:
        with httpx.Client(base_url="http://localhost:8000") as client:
            response = client.post("/api/v1/rates/calculate", json=_VALID_RATE_PAYLOAD)
        assert response.status_code == 401

    def test_invalid_api_key_on_rates_returns_401(self) -> None:
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"apikey": "not-a-real-key"},
        ) as client:
            response = client.post("/api/v1/rates/calculate", json=_VALID_RATE_PAYLOAD)
        assert response.status_code == 401

    def test_admin_basic_auth_on_rates_returns_401(self) -> None:
        # rates-route only accepts key-auth; Basic Auth is not a valid credential
        # type for this route, so Kong returns 401 before ACL is evaluated.
        with httpx.Client(
            base_url="http://localhost:8000",
            auth=("admin-carol", "carol-adm-secret"),
        ) as client:
            response = client.post("/api/v1/rates/calculate", json=_VALID_RATE_PAYLOAD)
        assert response.status_code == 401

    def test_no_credentials_on_config_returns_401(self) -> None:
        with httpx.Client(base_url="http://localhost:8000") as client:
            response = client.get("/api/v1/config/system")
        assert response.status_code == 401

    def test_broker_api_key_on_config_returns_401(self) -> None:
        # config-route only accepts basic-auth; an API key is not a valid
        # credential type for this route, so Kong returns 401 before ACL is evaluated.
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"apikey": "bkr-alice-a1b2c3d4e5f6"},
        ) as client:
            response = client.get("/api/v1/config/system")
        assert response.status_code == 401
