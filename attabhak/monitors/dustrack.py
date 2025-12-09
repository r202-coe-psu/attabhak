import socket
import asyncio

class DustrakClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = None


    async def init(self):
        print('Initialing')
        try:
            self.socket = socket.socket()
            self.socket.connect((self.ip , self.port))
        except OSError as e:
            print('Unable to connect')
            await self.close()
            return False
        print('Initial successfully')
        return True


    async def setup(self):
        await self.init()
        await self.read_sn()
        response = await self.send_msg('XSCTJDGCDDNJTGV', 19)
        if len(response) == 572:
            print('Dustrak machine setup OK')
        else:
            print('Dustrak machine setup ERROR')
            return False


    async def close(self):
        if self.socket:
            self.socket.close()
        print('Cloesed')
    

    async def shutdown(self):
        await self.send_msg('MSHUTDOWN')
        await self.close()
        print('Shutdown!')


    async def send_msg(self, msg, response_line=2):
        #Send some data to remote server
        sreader = asyncio.StreamReader(self.socket)
        swriter = asyncio.StreamWriter(self.socket, {})

        try:
            swriter.write(f'{msg}\r\n')
            await swriter.drain()
            data = b''
            #Receive data
            for _ in range(response_line):
                res = await sreader.readline()
                data += res
        except OSError:
            print('Cannot recieve messages')
            return

        recieve = data.decode().strip()
        # print('Received : ', recieve)

        return recieve


    async def setzero(self):
        await self.stop_machine()
        await uasyncio.sleep_ms(1000)

        await self.send_msg('MZERO')
        await uasyncio.sleep_ms(1000)

        response_text = await self.send_msg('RMZEROING')
        try:
            response = response_text.split(',')
        except AttributeError:
            return {}
        print('Set zero prosess:')

        while int(response[0]) < 60:
            # await self.send_msg('MSTATE', 4)            
            response_text = await self.send_msg('RMZEROING')
            try:
                response = response_text.split(',')
            except AttributeError:
                return ''
            print(f'Zeroing complete {int(int(response[0])/60*100):d}%')
            await uasyncio.sleep_ms(1000)

        print('Zeroing successfully')
        zero_value = await self.zero_value()

        return zero_value


    async def stop_machine(self):
        #Stop running
        response = await self.send_msg('MSTOP')
        print(f'Machine stopped {response}')


    async def start_sensor(self):
        #Actual Flow (LPM)
        response = await self.send_msg('MSTOP')
        if response == 'OK':
            print('Machine stopped')
        await uasyncio.sleep_ms(1000)

        response = await self.send_msg('MSTART')
        if response == 'OK':
            print('Starting machine')
        await uasyncio.sleep_ms(30000)

    
    async def read_sensor(self):
        response = await self.send_msg('RMMEAS')
        print('read pm sensor response : ', response)
        try:
            response_list = response.split(',')
        except AttributeError:
            return {}

        data = {
            'runtime': response_list[0],
            'pm_1': response_list[1],
            'pm_2_5': response_list[2],
            'pm_4': response_list[3],
            'pm_10': response_list[4],
            'pm_total': response_list[5],
        }
        print('pm sensor data : ', data)
        
        return data


    async def read_sn(self):
        recieve = await self.send_msg('RDSN')
        print('serial number : ', recieve)


    async def zero_value(self):
        response_text = await self.send_msg('RMZERO')
        try:
            response = response_text.split(',')
        except AttributeError:
            return {}

        data = {'old_zero_value': response[0],
                'new_zero_value': response[2],}

        return data
