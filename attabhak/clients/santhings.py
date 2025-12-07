import aiocoap


class SanThingsClient:
    def __init__(self, base_url):
        self.base_url = base_url

    async def put(self, device_id):
        protocol = await aiocoap.Context.create_client_context()
        request = aiocoap.Message(
            code=aiocoap.PUT, uri=f"{self.base_url}/devices/{device_id}/action"
        )

        try:
            response = await protocol.request(request).response
            return response.payload.decode("utf-8")
        except Exception as e:
            print(f"Failed to perform PUT request: {e}")
            return None
