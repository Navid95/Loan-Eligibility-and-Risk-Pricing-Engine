from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from audit_log.domain.aggregates import CalculationRecord
from audit_log.domain.value_objects import CreditTier, District, Multiplier, Rate
from fastapi.testclient import TestClient

from .fakes import FakeCalculationRecordRepository

_BASE_DT = datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)
_FROM = "2026-05-01T00:00:00Z"
_TO = "2026-05-31T23:59:59Z"


def _make_record(
    *,
    calculated_at: datetime = _BASE_DT,
    credit_tier: CreditTier = CreditTier.A,
) -> CalculationRecord:
    return CalculationRecord(
        correlation_id=uuid4(),
        credit_tier=credit_tier,
        district=District("München"),
        base_rate=Rate(Decimal("1.03")),
        term_multiplier=Multiplier(Decimal("1.0")),
        credit_tier_multiplier=Multiplier(Decimal("1.05")),
        regional_risk_multiplier=Multiplier(Decimal("1.0")),
        final_rate=Rate(Decimal("1.0815")),
        calculated_at=calculated_at,
        recorded_at=datetime.now(UTC),
    )


class TestListRecordsEndpoint:
    def test_returns_200_with_empty_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _TO})
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 50

    def test_returns_record_within_date_range(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        record = _make_record()
        repo.seed(record)

        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _TO})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["correlation_id"] == str(record.correlation_id)

    def test_excludes_record_outside_date_range(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        repo.seed(_make_record(calculated_at=datetime(2025, 1, 1, tzinfo=UTC)))

        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _TO})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_response_shape_has_all_required_fields(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        repo.seed(_make_record())

        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _TO})
        item = resp.json()["items"][0]

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
            assert field in item, f"missing field: {field}"

    def test_credit_tier_serialised_as_string(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        repo.seed(_make_record(credit_tier=CreditTier.B))

        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _TO})
        assert resp.json()["items"][0]["credit_tier"] == "B"

    def test_pagination_total_reflects_all_matching_records(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        for i in range(5):
            repo.seed(_make_record(calculated_at=_BASE_DT + timedelta(minutes=i)))

        resp = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 1, "page_size": 2},
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

    def test_second_page_returns_different_items(
        self, client: TestClient, repo: FakeCalculationRecordRepository
    ) -> None:
        for i in range(4):
            repo.seed(_make_record(calculated_at=_BASE_DT + timedelta(minutes=i)))

        page1 = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 1, "page_size": 2},
        ).json()
        page2 = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 2, "page_size": 2},
        ).json()

        ids1 = {item["correlation_id"] for item in page1["items"]}
        ids2 = {item["correlation_id"] for item in page2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_from_equal_to_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/records", params={"from": _FROM, "to": _FROM})
        assert resp.status_code == 422

    def test_from_after_to_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/records", params={"from": _TO, "to": _FROM})
        assert resp.status_code == 422

    def test_missing_from_param_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/records", params={"to": _TO})
        assert resp.status_code == 422

    def test_missing_to_param_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/records", params={"from": _FROM})
        assert resp.status_code == 422

    def test_page_size_above_maximum_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page_size": 101},
        )
        assert resp.status_code == 422

    def test_page_below_minimum_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page": 0},
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("page_size", [1, 50, 100])
    def test_valid_page_sizes_are_accepted(
        self, client: TestClient, page_size: int
    ) -> None:
        resp = client.get(
            "/api/v1/records",
            params={"from": _FROM, "to": _TO, "page_size": page_size},
        )
        assert resp.status_code == 200
        assert resp.json()["page_size"] == page_size
