import asyncio

from attabhak.server import Server


def main():
    server = Server()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        asyncio.run(server.stop())
