import datetime
import logging
import asyncio


from .monitors import dustrack
from .config import settings

from .clients.santhings import SanThingsClient


class Server:
    def __init__(self):
        self.running = False
        self.logger = logging.getLogger("attabhak.server")
        self.monitor_tasks = []
        self.interval = settings.INTERVAL

    async def set_up(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        self.dustrack = dustrack.DustrakClient(
            settings.DUSTRACT_HOST, settings.DUSTRACT_PORT
        )
        await self.dustrack.setup()

        self.santhings = SanThingsClient(
            settings.SANTHINGS_DEVICE_ID, settings.SANTHINGS_SECRET_KEY, settings
        )
        await self.santhings.auth()

    async def start(self):

        self.running = True
        self.logger.info(f"Server started")
        await self.run()

    async def run(self):
        await self.set_up()
        while self.running:
            self.logger.debug("Waiting for commands...")
            data = await self.dustrack.read_sensor()
            print("Dustrak data:", data)
            await asyncio.sleep(self.interval)

    async def stop(self):
        self.logger.info(f"Trying to stop server...")

        self.running = False
        self.logger.info(f"Server stopped")
