import aiocoap

import json


class SanThingsClient:
    def __init__(self, device_id, secret_key, settings):
        self.device_id = device_id
        self.secret_key = secret_key
        self.host_uri = settings.SANTHINGS_COAP_URI

        self.data_interval = 1
        print("SanThingsClient initialized", settings)

    async def auth(self):
        print("Beginning Authentication")
        payload = {
            "device_id": self.device_id,
            "secret_key": self.secret_key,
        }
        host_uri = f"{self.host_uri}/v1/device_auth"

        protocol = await aiocoap.Context.create_client_context()
        request = aiocoap.Message(
            code=aiocoap.POST,
            uri=self.host_uri,
            payload=json.dumps(payload).encode("utf-8"),
        )
        response = await protocol.request(request).response
        response_data = json.loads(response.payload.decode("utf-8"))

        print("santhings response data : ", response_data)
        if "access_token" in response_data:
            self.access_token = response_data["access_token"]
        else:
            self.access_token = ""
            return ""
        # self.refresh_token = response_data['refresh_token']
        print(f"access_token : {self.access_token}")
        print("Authentication OK")

        return self.access_token

    async def get_settings(self):
        payload = {
            "device_id": self.device_id,
            "secret_key": self.secret_key,
        }

    async def build_payload(self, data={}):
        payload = {
            "access_token": self.access_token,
            "data": data,
        }
        # payload_json = json.dumps(payload)
        # payload_json_hex = await self.coap_client.string_to_hex(payload_json)

        return payload

    async def upload_data(self, data):

        print("Data uploade OK")

        return ""
