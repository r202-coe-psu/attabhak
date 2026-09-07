import aiocoap
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class SanThingsClient:
    def __init__(self, device_id, secret_key, settings):
        self.device_id = device_id
        self.secret_key = secret_key
        self.host_uri = settings.SANTHINGS_COAP_URI

        self.access_token = ""
        self.refresh_token = ""
        self.data_interval = 1
        logger.debug("SanThingsClient initialized for device %s", self.device_id)

    async def auth(self):
        logger.info("Beginning authentication")
        payload = {
            "device_id": self.device_id,
            "secret_key": self.secret_key,
        }
        endpoint_uri = f"{self.host_uri}/v2/auth"

        protocol = await aiocoap.Context.create_client_context()
        request = aiocoap.Message(
            code=aiocoap.POST,
            uri=endpoint_uri,
            payload=json.dumps(payload).encode("utf-8"),
        )

        try:
            response = await protocol.request(request).response
        except Exception as e:
            logger.exception(e)
            self.access_token = ""
            self.refresh_token = ""
            return
        finally:
            await protocol.shutdown()

        response_data = json.loads(response.payload.decode("utf-8"))

        if response.code.is_successful():
            self.access_token = response_data.get("access_token", "")
            self.refresh_token = response_data.get("refresh_token", "")

    async def get_settings(self):

        endpoint_uri = f"{self.host_uri}/v2/settings?access_token={self.access_token}"

        protocol = await aiocoap.Context.create_client_context()
        request = aiocoap.Message(
            code=aiocoap.GET,
            uri=endpoint_uri,
        )

        try:
            response = await protocol.request(request).response
        except Exception as e:
            logger.exception(e)
            return dict()
        finally:
            await protocol.shutdown()

        if not response.code.is_successful():
            return dict()

        response_data = json.loads(response.payload.decode("utf-8"))
        return response_data

    async def send(self, data):
        endpoint_uri = (
            f"{self.host_uri}/v2/telemetries?access_token={self.access_token}"
        )
        payload = dict(data=data)

        protocol = await aiocoap.Context.create_client_context()
        request = aiocoap.Message(
            code=aiocoap.POST,
            uri=endpoint_uri,
            payload=json.dumps(payload).encode("utf-8"),
        )
        try:
            response = await protocol.request(request).response
        except Exception as e:
            logger.exception(e)
            return False
        finally:
            await protocol.shutdown()

        if response.code.is_successful():
            return True

        if response.code in [
            aiocoap.numbers.codes.Code.FORBIDDEN,
            aiocoap.numbers.codes.Code.UNAUTHORIZED,
        ]:
            await self.auth()

        return False
