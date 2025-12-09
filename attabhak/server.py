import datetime
import logging
import asyncio

from .monitors import dustrack


class Server:
    def __init__(self):
        self.running = False
        self.logger = logging.getLogger("attabhak.server")
        self.monitor_tasks = []


        self.config = dict(
            broker_url="localhost",
            topic="sensors/#",
        )

    async def set_up(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        self.dustrack = dustrack.DustrakClient(ip="192.168.8.1", port=55832)
        await self.dustrack.init()
        await self.dustrack.setup()

    async def start(self):


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
