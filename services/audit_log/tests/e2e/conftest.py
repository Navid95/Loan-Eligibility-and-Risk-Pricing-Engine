import asyncio
import json
import os
from collections.abc import Generator

import aio_pika
import httpx
import pytest

_KONG_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
_RABBITMQ_URL = os.environ.get(
    "E2E_RABBITMQ_URL", "amqp://nordvik:nordvik@localhost:5672/"
)


@pytest.fixture(scope="module")
def audit_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(
        base_url=_KONG_URL,
        auth=httpx.BasicAuth("auditor-alice", "alice-aud-secret"),
    ) as client:
        yield client


@pytest.fixture(scope="module")
def publish_event():
    def _publish(payload: dict) -> None:
        async def _inner() -> None:
            conn = await aio_pika.connect_robust(_RABBITMQ_URL)
            async with conn:
                channel = await conn.channel()
                exchange = await channel.get_exchange("audit.events")
                await exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(payload).encode(),
                        content_type="application/json",
                    ),
                    routing_key="calculation.completed",
                )

        asyncio.run(_inner())

    return _publish
