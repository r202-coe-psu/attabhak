import aiomqtt
import asyncio
import datetime
import json
import logging

logger = logging.getLogger("attabhak")

DEFAULT_TOPIC = "notif/ControlService.MonitorFactorAll"

UNUSED_KEYS = ["aqi", "error", "event", "task_id", "task_type", "timestamp"]
REPLACED_KEYS = dict(
    ambient_humid="humidity",
    ambient_press="pressure",
    ambient_temp="temperature",
    so2="SO2",
    so2_mg="SO2_mg",
    so2_aver="SO2_avg",
    so2_aver_mg="SO2_avg_mg",
    o3="O3",
    o3_mg="O3_mg",
    o3_aver="O3_avg",
    o3_aver_mg="O3_avg_mg",
    no2="NO2",
    no2_mg="NO2_mg",
    no2_aver="NO2_avg",
    no2_aver_mg="NO2_avg_mg",
    co="CO",
    co_mg="CO_mg",
    co_aver="CO_avg",
    co_aver_mg="CO_avg_mg",
    pm25="pm_2_5",
    pm25_aver="pm_2_5_avg",
    pm10="pm_10",
    pm10_aver="pm_10_avg",
)


class Apm6Client:
    def __init__(self, broker_url, port=1883, topic=DEFAULT_TOPIC):
        self.broker_url = broker_url
        self.port = port
        self.topic = topic
        self.data: dict = {}
        self.listen_task = None
        self.datas = asyncio.Queue(maxsize=100)

    async def setup(self):
        self.listen_task = asyncio.create_task(self._listen())
        logger.debug("APM6 listener started")
        return True

    async def _listen(self):
        while True:
            try:
                async with aiomqtt.Client(self.broker_url, port=self.port) as client:
                    logger.debug(
                        "Connected to APM6 MQTT broker at %s:%s",
                        self.broker_url,
                        self.port,
                    )
                    await client.subscribe(self.topic)
                    logger.info("APM6 subscribed to topic: %s", self.topic)
                    async for message in client.messages:
                        await self._parse_message(message)

            except aiomqtt.MqttError as e:
                logger.warning("APM6 MQTT connection lost, retrying: %s", e)
                await asyncio.sleep(5)

    async def _parse_message(self, message):
        # print('Received message:', message.payload)

        try:
            payload = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Received malformed APM6 payload: %r", message.payload)
            return {}

        data = payload.get("data", {})

        if not data:
            logger.warning("Received empty APM6 payload")
            return

        response = dict()
        for k, v in data.items():

            if k == "timestamp":
                response["runtime"] = v
                continue

            if k in UNUSED_KEYS:
                continue

            if "_temp" not in k and v < 0:
                continue

            key = REPLACED_KEYS.get(k, k)
            response[key] = v / 10  # ten minuts measure 1

        for k, v in data.items():
            if "aver" not in k:
                continue

            sk = k.split("aver")[0].replace("_", "").strip()
            sk = REPLACED_KEYS.get(sk, sk)
            if sk not in response:
                response.pop(REPLACED_KEYS.get(k, k))

        response["timestamp"] = datetime.datetime.now(datetime.timezone.utc).timestamp()

        await self.datas.put(response)

    async def read_sensor(self):
        return await self.datas.get()

    async def close(self):
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        logger.debug("APM6 client stopped")
