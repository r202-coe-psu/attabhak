import asyncio

from attabhak.server import Server


async def run(server: Server):
    try:
        await server.start()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()


def main():
    server = Server()
    asyncio.run(run(server))
