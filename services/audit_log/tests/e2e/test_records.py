import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx

_FROM = "2026-01-01T00:00:00Z"
_TO = "2027-01-01T00:00:00Z"

_BASE_PAYLOAD = {
    "credit_tier": "A",
    "district": "München",
    "base_rate": "5.000000",
    "term_multiplier": "1.000000",
    "credit_tier_multiplier": "0.950000",
    "regional_risk_multiplier": "1.100000",
    "final_rate": "5.225000",
}


def _make_payload(**overrides: str) -> dict:
    return {
        "correlation_id": str(uuid4()),
        **_BASE_PAYLOAD,
        "calculated_at": datetime.now(UTC).isoformat(),
        **overrides,
    }


def _poll_for_record(
    client: httpx.Client,
    *,
    correlation_id: str,
    max_seconds: int = 15,
) -> dict:
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        resp = client.get(
            "/api/v1/records", params={"from": _FROM, "to": _TO, "page_size": 100}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            if item["correlation_id"] == correlation_id:
                return item
        time.sleep(0.5)
    raise TimeoutError(
        f"record {correlation_id} did not appear in audit_log within {max_seconds}s"
    )


class TestListRecordsValidation:
    def test_missing_from_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get("/api/v1/records", params={"to": _TO})
        assert resp.status_code == 422

    def test_missing_to_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get("/api/v1/records", params={"from": _FROM})
        assert resp.status_code == 422

    def test_from_equal_to_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get("/api/v1/records", params={"from": _FROM, "to": _FROM})
        assert resp.status_code == 422

    def test_from_after_to_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get("/api/v1/records", params={"from": _TO, "to": _FROM})
        assert resp.status_code == 422

    def test_page_size_above_100_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page_size": 101},
        )
        assert resp.status_code == 422

    def test_page_below_1_returns_422(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 0},
        )
        assert resp.status_code == 422


class TestCalculationRecordFlow:
    def test_calculation_appears_in_audit_log(
        self,
        audit_client: httpx.Client,
        publish_event,
    ) -> None:
        payload = _make_payload(credit_tier="A", district="München")
        publish_event(payload)

        cid = payload["correlation_id"]
        record = _poll_for_record(audit_client, correlation_id=cid)

        assert record["correlation_id"] == payload["correlation_id"]
        assert record["credit_tier"] == "A"
        assert record["district"] == "München"

    def test_record_carries_full_rate_breakdown(
        self,
        audit_client: httpx.Client,
        publish_event,
    ) -> None:
        payload = _make_payload(credit_tier="B")
        publish_event(payload)

        cid = payload["correlation_id"]
        record = _poll_for_record(audit_client, correlation_id=cid)

        assert record["base_rate"] == payload["base_rate"]
        assert record["term_multiplier"] == payload["term_multiplier"]
        assert record["credit_tier_multiplier"] == payload["credit_tier_multiplier"]
        rrm = record["regional_risk_multiplier"]
        assert rrm == payload["regional_risk_multiplier"]
        assert record["final_rate"] == payload["final_rate"]

    def test_duplicate_correlation_id_produces_one_record(
        self,
        audit_client: httpx.Client,
        publish_event,
    ) -> None:
        cid = str(uuid4())
        payload = _make_payload(correlation_id=cid, credit_tier="C")
        publish_event(payload)
        publish_event(payload)

        _poll_for_record(audit_client, correlation_id=cid)

        resp = audit_client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page_size": 100},
        )
        ids = [item["correlation_id"] for item in resp.json()["items"]]
        assert ids.count(cid) == 1

    def test_records_response_shape(
        self,
        audit_client: httpx.Client,
        publish_event,
    ) -> None:
        payload = _make_payload(credit_tier="A")
        publish_event(payload)

        cid = payload["correlation_id"]
        record = _poll_for_record(audit_client, correlation_id=cid)

        for field in (
            "correlation_id",
            "credit_tier",
            "district",
            "base_rate",
            "term_multiplier",
            "credit_tier_multiplier",
            "regional_risk_multiplier",
            "final_rate",
            "calculated_at",
            "recorded_at",
        ):
            assert field in record, f"missing field in audit record: {field}"

    def test_pagination_metadata_is_correct(self, audit_client: httpx.Client) -> None:
        resp = audit_client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 1, "page_size": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 5
        assert "total" in body
        assert "items" in body
