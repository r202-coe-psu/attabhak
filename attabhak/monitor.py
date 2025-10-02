import aiomqtt
import logging
import asyncio


class MQTTMonitor:
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.logger = logging.getLogger("attabhak.monitor")

    async def monitor(self, topic: str):
        while True:
            self.logger.info(f"Monitoring topic: {topic}")
            await asyncio.sleep(1)
        # async with aiomqtt.Client(self.broker_url) as client:
        #     await client.subscribe(topic)
        #     async for message in client.messages:
        #         self.logger.info(
        #             f"Received message on {message.topic}: {message.payload.decode()}"
        #         )
