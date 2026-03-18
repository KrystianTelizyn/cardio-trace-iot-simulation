from __future__ import annotations

from typing import Optional

from aiomqtt import Client as AioMqttClient


class AioMqttClientAdapter:
    def __init__(self, hostname: str, port: int = 1883):
        self.hostname = hostname
        self.port = port
        self._client: Optional[AioMqttClient] = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = AioMqttClient(hostname=self.hostname, port=self.port)
        await self._client.__aenter__()  # aiomqtt connects via async context manager

    async def disconnect(self) -> None:
        if self._client is None:
            return
        client = self._client
        self._client = None
        await client.__aexit__(None, None, None)

    async def publish(
        self, topic: str, payload: str, qos: int = 0, retain: bool = False
    ) -> None:
        if self._client is None:
            raise RuntimeError("MQTT client is not connected")
        await self._client.publish(topic, payload=payload, qos=qos, retain=retain)
