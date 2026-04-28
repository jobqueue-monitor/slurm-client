import datetime as dt
from dataclasses import dataclass

import asyncssh
import httpx

from slurm_client.rest_api.token import Token


@dataclass
class SSHConnection:
    handle: asyncssh.SSHClientConnection

    async def close(self):
        self.handle.close()
        await self.handle.wait_closed()


@dataclass
class SocksProxy:
    listener: asyncssh.SSHListener

    def to_url(self):
        return f"http://localhost:{self.listener.get_port()}"

    async def close(self):
        self.listener.close()

        await self.listener.wait_closed()


@dataclass
class Connection:
    ssh: asyncssh.SSHClientConnection
    socks_proxy: SocksProxy
    api: httpx.AsyncClient

    async def close(self):
        await self.api.aclose()
        await self.socks_proxy.close()
        await self.ssh.close()


async def create_socks_proxy(con: SSHConnection) -> SocksProxy:
    listener = await con.handle.forward_socks("127.0.0.1", 0)

    return SocksProxy(listener)


async def connect(server: str) -> Connection:
    ssh = SSHConnection(await asyncssh.connect(server))
    socks_proxy = await create_socks_proxy(ssh)
    api = httpx.AsyncClient()

    return Connection(ssh, socks_proxy, api)


async def refresh_token(con: SSHConnection, lifespan: dt.timedelta) -> Token:
    now = dt.datetime.now(tz=dt.UTC)

    result = await con.handle.run(
        f"scontrol token lifespan={int(lifespan.total_seconds())}", check=True
    )
    return Token.from_expr(result.stdout.strip(), now + lifespan)
