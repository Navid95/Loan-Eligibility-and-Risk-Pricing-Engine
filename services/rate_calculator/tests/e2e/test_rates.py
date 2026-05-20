import json
import re
import time
from decimal import Decimal

import httpx
import pytest

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class TestRatesEndpoint:
    def test_calculate_rate_returns_200_with_full_breakdown(
        self, broker_client: httpx.Client
    ) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "80331", "loan_term_months": 36, "credit_tier": "A"},
        )

        assert response.status_code == 200
        data = response.json()
        for field in (
            "correlation_id",
            "final_rate",
            "base_rate",
            "term_multiplier",
            "credit_tier_multiplier",
            "regional_risk_multiplier",
            "district",
            "calculated_at",
        ):
            assert field in data, f"missing field: {field}"

        assert Decimal(data["base_rate"]) == Decimal("1.03")
        assert Decimal(data["term_multiplier"]) == Decimal("1.0")
        assert Decimal(data["credit_tier_multiplier"]) == Decimal("1.05")
        assert data["district"] == "München"
        expected_final = (
            Decimal(data["base_rate"])
            * Decimal(data["term_multiplier"])
            * Decimal(data["credit_tier_multiplier"])
            * Decimal(data["regional_risk_multiplier"])
        )
        assert Decimal(data["final_rate"]) == expected_final

    def test_correlation_id_is_a_kong_generated_uuid(
        self, broker_client: httpx.Client
    ) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "80331", "loan_term_months": 12, "credit_tier": "B"},
        )

        assert response.status_code == 200
        correlation_id = response.json()["correlation_id"]
        assert _UUID4_RE.match(correlation_id), (
            f"correlation_id is not a UUID4: {correlation_id}"
        )

    @pytest.mark.parametrize(
        "loan_term_months, expected_multiplier",
        [
            (12, "0.8"),
            (24, "1.0"),
            (48, "1.3"),
            (72, "1.7"),
        ],
    )
    def test_term_multiplier_applied_correctly(
        self,
        broker_client: httpx.Client,
        loan_term_months: int,
        expected_multiplier: str,
    ) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={
                "postal_code": "80331",
                "loan_term_months": loan_term_months,
                "credit_tier": "B",
            },
        )

        assert response.status_code == 200
        assert Decimal(response.json()["term_multiplier"]) == Decimal(
            expected_multiplier
        )

    def test_invalid_postal_code_format_returns_422(
        self, broker_client: httpx.Client
    ) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "ABCDE", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 422

    def test_unknown_postal_code_returns_404(self, broker_client: httpx.Client) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "00000", "loan_term_months": 12, "credit_tier": "A"},
        )

        assert response.status_code == 404

    def test_invalid_credit_tier_returns_422(self, broker_client: httpx.Client) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "79100", "loan_term_months": 12, "credit_tier": "X"},
        )

        assert response.status_code == 422


def _poll_amqp_message(
    mgmt: httpx.Client,
    *,
    queue: str = "audit.calculations",
    correlation_id: str,
    max_seconds: int = 15,
) -> dict:
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        resp = mgmt.post(
            f"/api/queues/%2F/{queue}/get",
            json={"count": 100, "ackmode": "ack_requeue_true", "encoding": "auto"},
        )
        resp.raise_for_status()
        for msg in resp.json():
            payload = json.loads(msg["payload"])
            if payload.get("correlation_id") == correlation_id:
                return payload
        time.sleep(0.5)
    raise TimeoutError(
        f"no AMQP message for {correlation_id} on {queue} within {max_seconds}s"
    )


class TestRabbitMQPublication:
    def test_successful_calculation_publishes_event(
        self, broker_client: httpx.Client, mgmt_client: httpx.Client
    ) -> None:
        response = broker_client.post(
            "/api/v1/rates/calculate",
            json={"postal_code": "80331", "loan_term_months": 24, "credit_tier": "A"},
        )
        assert response.status_code == 200
        data = response.json()
        correlation_id = data["correlation_id"]

        msg = _poll_amqp_message(mgmt_client, correlation_id=correlation_id)

        assert msg["correlation_id"] == correlation_id
        assert msg["credit_tier"] == "A"
        assert msg["district"] == "München"
        assert msg["base_rate"] == data["base_rate"]
        assert msg["term_multiplier"] == data["term_multiplier"]
        assert msg["credit_tier_multiplier"] == data["credit_tier_multiplier"]
        assert msg["regional_risk_multiplier"] == data["regional_risk_multiplier"]
        assert msg["final_rate"] == data["final_rate"]
        assert "calculated_at" in msg
