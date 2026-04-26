import datetime as dt
import re
from dataclasses import dataclass
from typing import ClassVar, Self

import asyncssh
import httpx


@dataclass
class Token:
    token: str
    valid_until: dt.datetime

    token_expr_re: ClassVar[re.Pattern] = re.compile(r"SLURM_JWT=(.+)")

    @classmethod
    def from_expr(cls, expr: str, valid_until: dt.datetime) -> Self:
        match = cls.token_expr_re.fullmatch(expr)
        if match is None:
            raise ValueError(f"invalid token expression: {expr}")

        token = match.group(1)

        return cls(token, valid_until)

    def is_valid(self):
        now = dt.datetime.now(tz=dt.UTC)

        return now + dt.timedelta(seconds=1) < self.valid_until

    def __str__(self):
        return self.token


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

    async def refresh_token(self, lifespan: dt.timedelta) -> Token:
        now = dt.datetime.now(tz=dt.UTC)

        result = await self.ssh.handle.run(
            f"scontrol token lifespan={int(lifespan.total_seconds())}", check=True
        )
        return Token.from_expr(result.stdout.strip(), now + lifespan)


async def create_socks_proxy(con: SSHConnection) -> SocksProxy:
    listener = await con.handle.forward_socks("127.0.0.1", 0)

    return SocksProxy(listener)


async def connect(server: str) -> Connection:
    ssh = SSHConnection(await asyncssh.connect(server))
    socks_proxy = await create_socks_proxy(ssh)
    api = httpx.AsyncClient()

    return Connection(ssh, socks_proxy, api)
