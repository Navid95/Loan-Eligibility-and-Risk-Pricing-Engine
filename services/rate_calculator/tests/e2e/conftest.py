import os
from collections.abc import Generator

import httpx
import pytest

_BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
_MGMT_URL = os.environ.get("E2E_MGMT_URL", "http://localhost:15672")

_BROKER_API_KEY = "bkr-alice-a1b2c3d4e5f6"
_ADMIN_USERNAME = "admin-carol"
_ADMIN_PASSWORD = "carol-adm-secret"


@pytest.fixture(scope="module")
def broker_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=_BASE_URL,
        headers={"apikey": _BROKER_API_KEY},
    ) as client:
        yield client


@pytest.fixture(scope="module")
def admin_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=_BASE_URL,
        auth=(_ADMIN_USERNAME, _ADMIN_PASSWORD),
    ) as client:
        yield client


@pytest.fixture(scope="module")
def mgmt_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=_MGMT_URL,
        auth=("nordvik", "nordvik"),
    ) as client:
        yield client
