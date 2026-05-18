import json

import aio_pika
from aio_pika.abc import AbstractRobustConnection


class RabbitMQPublisher:
    def __init__(self, rabbitmq_url: str, exchange_name: str, routing_key: str) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._exchange_name = exchange_name
        self._routing_key = routing_key
        self._connection: AbstractRobustConnection | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)
        channel = await self._connection.channel()
        self._exchange = await channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish(self, payload: dict[str, str]) -> None:
        if self._exchange is None:
            raise RuntimeError("publisher not connected — call connect() first")
        body = json.dumps(payload).encode()
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=self._routing_key)
