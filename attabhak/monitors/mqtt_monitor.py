import aiomqtt
import logging
import asyncio


class MQTTMonitor:
    def __init__(self, broker_url: str = "localhost:1883", topic: str = "sensors/#"):
        self.broker_url = broker_url
        self.topic = topic
        # self.logger = logging.getLogger("attabhak.monitor")
        self.logger = logging.getLogger(__name__)

    async def run(self):
        self.logger.info(
            f"Starting MQTT Monitor on {self.broker_url}, topic: {self.topic}"
        )
        async with aiomqtt.Client(self.broker_url) as client:
            self.logger.info(f"Connected to MQTT broker at {self.broker_url}")
            await client.subscribe(self.topic)
            self.logger.info(f"Subscribed to topic: {self.topic}")
            async for message in client.messages:
                self.logger.debug("Received MQTT message")
                self.logger.info(
                    f"Received message on {message.topic}: {message.payload.decode()}"
                )
        self.logger.info("MQTT Monitor stopped")

    async def stop(self):
        self.logger.info("Stopping MQTT Monitor")
