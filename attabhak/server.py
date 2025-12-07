import datetime
import logging
import asyncio

from . import monitor


class Server:
    def __init__(self):
        self.running = False
        self.logger = logging.getLogger("attabhak.server")
        self.monitor_tasks = []
        self.monitors = []

        self.config = dict(
            broker_url="localhost",
            topic="sensors/#",
        )

    async def set_up(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    async def start(self):
        mqtt_monitor = monitor.MQTTMonitor(
            self.config.get("broker_url"), self.config.get("topic")
        )
        self.monitors.append(mqtt_monitor)

        self.monitor_tasks.append(asyncio.create_task(mqtt_monitor.run()))

        self.running = True
        self.logger.info(f"Server started")
        await self.run()

    async def run(self):
        await self.set_up()
        while self.running:
            self.logger.debug("Waiting for commands...")
            await asyncio.sleep(1)

    async def stop(self):
        self.logger.info(f"Trying to stop server...")
        for monitor in self.monitors:
            await monitor.stop()

        for task in self.monitor_tasks:
            try:
                task.cancel()
            except asyncio.CancelledError:
                logging.exception("Monitor task cancelled")

        self.running = False
        self.logger.info(f"Server stopped")
