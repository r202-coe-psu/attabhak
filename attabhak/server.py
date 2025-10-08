import datetime
import logging
import asyncio

from . import monitor


class Server:
    def __init__(self):
        self.running = False
        self.logger = logging.getLogger("attabhak.server")
        self.monitor_tasks = []

        self.config = dict()

    async def start(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        self.monitor_tasks.append(
            asyncio.create_task(
                monitor.MQTTMonitor(
                    self.config.get("broker_url"), self.config.get("topic")
                ).run()
            )
        )

        self.running = True
        self.logger.info(f"Server started")
        await self.run()

    async def run(self):
        while self.running:
            self.logger.debug("Waiting for commands...")
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        self.logger.info(f"Server stopped")
