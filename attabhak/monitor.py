import aiomqtt
import logging
import asyncio


class MQTTMonitor:
    def __init__(self, broker_url: str, topic: str = "sensors/#"):
        self.broker_url = broker_url
        self.topic = topic
        self.logger = logging.getLogger("attabhak.monitor")

    async def run(self):
        async with aiomqtt.Client(self.broker_url) as client:
            await client.subscribe(self.topic)
            async for message in client.messages:
                self.logger.info(
                    f"Received message on {message.topic}: {message.payload.decode()}"
                )
