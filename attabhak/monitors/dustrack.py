import asyncio
import datetime


class DustrakClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.reader = None
        self.writer = None

    async def init(self):
        print("Initialing")
        try:
            self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        except (OSError, asyncio.TimeoutError):
            print("Unable to connect")
            await self.close()
            return False

        print("Initial successfully")
        return True

    async def setup(self):
        await self.init()
        sn = await self.read_sn()
        if sn:
            print("Dustrak machine SN:", sn)
            return True

        print("Dustrak machine SN read ERROR")
        return False

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        print("Closed")

    async def shutdown(self):
        await self.send_msg("MSHUTDOWN")
        await self.close()
        print("Shutdown!")

    async def send_msg(self, msg, response_line=2):
        if not self.writer or self.writer.is_closing():
            print("Socket is not connected")
            return

        try:
            self.writer.write(f"{msg}\r\n".encode())
            await self.writer.drain()
            data = bytearray()
            for _ in range(response_line):
                res = await self.reader.readline()
                if not res:
                    break
                data.extend(res)
        except OSError:
            print("Cannot receive messages")
            return

        return data.decode().strip()

    async def setzero(self):
        await self.stop_machine()
        await asyncio.sleep(1)

        await self.send_msg("MZERO")
        await asyncio.sleep(1)

        response_text = await self.send_msg("RMZEROING")
        try:
            response = response_text.split(",")
        except AttributeError:
            return {}
        print("Set zero prosess:")

        while int(response[0]) < 60:
            response_text = await self.send_msg("RMZEROING")
            try:
                response = response_text.split(",")
            except AttributeError:
                return ""
            print(f"Zeroing complete {int(int(response[0]) / 60 * 100):d}%")
            await asyncio.sleep(1)

        print("Zeroing successfully")
        return await self.zero_value()

    async def stop_machine(self):
        response = await self.send_msg("MSTOP")
        print(f"Machine stopped {response}")

    async def start_sensor(self):
        response = await self.send_msg("MSTOP")
        if response == "OK":
            print("Machine stopped")
        await asyncio.sleep(1)

        response = await self.send_msg("MSTART")
        if response == "OK":
            print("Starting machine")
        await asyncio.sleep(30)

    async def read_sensor(self):
        response = await self.send_msg("RMMEAS")
        # print('read pm sensor response : ', response)
        try:
            response_list = response.split(",")
        except AttributeError:
            return {}

        data = {
            "timestamp": datetime.datetime.now().timestamp(),
            "runtime": response_list[0],
            "pm_1": response_list[1],
            "pm_2_5": response_list[2],
            "pm_4": response_list[3],
            "pm_10": response_list[4],
            "pm_total": response_list[5],
        }
        # print('pm sensor data : ', data)

        return data

    async def read_sn(self):
        receive = await self.send_msg("RDSN")
        print("serial number : ", receive)
        return receive

    async def zero_value(self):
        response_text = await self.send_msg("RMZERO")
        try:
            response = response_text.split(",")
        except AttributeError:
            return {}

        return {
            "old_zero_value": response[0],
            "new_zero_value": response[2],
        }
