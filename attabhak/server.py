import datetime
import logging
import asyncio
import pathlib


from .monitors import dustrack
from .config import settings
from . import model
from sqlmodel import select

from .clients.santhings import SanThingsClient

import logging

logger = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.running: bool = False
        self.logger = logging.getLogger("attabhak.server")
        self.monitor_tasks: list = []
        self.interval: int = settings.INTERVAL
        self.queue: asyncio.Queue = asyncio.Queue()
        self.upload_task = None
        self.update_configuration_task = None
        self.max_queue_size: int = 50

    async def set_up(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            handlers=[logging.StreamHandler()],
        )

        logging.getLogger("attabhak").setLevel(logging.DEBUG)
        for logger_name in logging.root.manager.loggerDict:
            if not logger_name.startswith("attabhak"):
                logging.getLogger(logger_name).setLevel(logging.WARNING)

        pathlib.Path("./data").mkdir(parents=True, exist_ok=True)

        await model.create_db_and_tables()
        await self.connect_dustrack()
        await self.connect_santhings()

        self.upload_task = asyncio.create_task(self.upload_data())
        self.update_configuration_task = asyncio.create_task(
            self.update_configuration()
        )

    async def connect_dustrack(self):

        try:
            self.dustrack = dustrack.DustrakClient(
                settings.DUSTRACT_HOST, settings.DUSTRACT_PORT
            )
            await self.dustrack.setup()
        except Exception as e:
            logger.exception(e)

    async def connect_santhings(self):
        try:
            self.santhings = SanThingsClient(
                settings.SANTHINGS_DEVICE_ID, settings.SANTHINGS_SECRET_KEY, settings
            )
            await self.santhings.auth()
            await self.update_santhings_configuration()
        except Exception as e:
            logger.exception(e)

    async def update_santhings_configuration(self):
        try:
            self.santhings_settings = await self.santhings.get_settings()
            self.interval = self.santhings_settings.get("data_interval", self.interval)
        except Exception as e:
            logger.exception(e)

    async def start(self):

        self.running = True
        self.logger.info(f"Server started wait for 1m")
        await asyncio.sleep(60)
        await self.run()

    async def run(self):
        await self.set_up()
        while self.running:
            data = await self.dustrack.read_sensor()
            await self.queue.put(data)
            await asyncio.sleep(self.interval)
            # await asyncio.sleep(1)

    async def stop(self):
        self.logger.info(f"Trying to stop server...")
        self.running = False
        await asyncio.sleep(1)

        self.upload_task.cancel()
        self.update_configuration_task.cancel()
        self.logger.info(f"Server stopped")

    async def store_data(self, data):
        async with model.get_session() as session:
            sensor_data = model.SensorData(data=data)
            session.add(sensor_data)
            await session.commit()

    async def restore_data(self):
        async with model.get_session() as session:
            statement = select(model.SensorData).limit(1)
            result = await session.execute(statement)
            sensor_data = result.scalars().first()
            if sensor_data:
                await session.delete(sensor_data)
                await session.commit()
                return sensor_data.data
        return None

    async def upload_data(self):
        last_runtime = 0
        while self.running:
            logger.debug(
                f"upload data, queue size: {self.queue.qsize()} max size: {self.max_queue_size}"
            )
            if self.queue.qsize() < self.max_queue_size // 2:
                while self.queue.qsize() <= self.max_queue_size:

                    try:
                        data = await self.restore_data()
                    except Exception as e:
                        logger.exception(f"Error restoring data: {e}")
                        break

                    if not data:
                        break

                    logger.debug(f"restore data: {data}")
                    await self.queue.put(data)

            if self.queue.empty():
                await asyncio.sleep(10)
                continue

            data = await self.queue.get()
            if data.get("runtime") != last_runtime:
                result = None
                try:
                    if self.santhings:
                        result = await self.santhings.send(data)
                        logger.debug(f"send: {result} {data}")
                        last_runtime = data.get("runtime")
                except Exception as e:
                    logger.exception(e)

                if not result:
                    logger.debug(f"re-queue data: {data}")

                    await self.queue.put(data)
                    # await asyncio.sleep(120)
            else:
                logger.debug(f"drop : {data}")

            while self.queue.qsize() > self.max_queue_size:
                data = await self.queue.get()
                logger.debug(f"store data: {data}")
                try:
                    await self.store_data(data)
                except Exception as e:
                    logger.exception(f"Error storing data: {e}")

    async def update_configuration(self):
        wait_time = 60 * 60  # in second
        while self.running:
            logger.debug("update santhings configuration")
            await self.update_santhings_configuration()
            await asyncio.sleep(wait_time)
