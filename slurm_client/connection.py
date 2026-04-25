import datetime as dt
import re
from dataclasses import dataclass
from typing import ClassVar, Self

import asyncssh


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

        token = match.group(0)

        return cls(token, valid_until)

    def is_valid(self):
        now = dt.datetime.now(tz=dt.UTC)

        return now + dt.timedelta(seconds=1) < self.valid_until


@dataclass
class SocksProxy:
    handle: asyncssh.SSHListener

    def to_proxy_url(self):
        return f"http://localhost:{self.handle.get_port()}"


@dataclass
class Connection:
    handle: asyncssh.SSHClientConnection

    async def close(self):
        self.handle.close()
        await self.handle.wait_closed()


async def refresh_token(con: Connection, lifespan: dt.timedelta) -> Token:
    now = dt.datetime.now(tz=dt.UTC)

    result = await con.handle.run(
        f"scontrol token lifespan={int(lifespan.total_seconds())}", check=True
    )
    return Token.from_expr(result.stdout.strip(), now + lifespan)


async def create_socks_proxy(con: asyncssh.Connection) -> SocksProxy:
    handle = await con.handle.forward_socks("localhost", 0)

    return SocksProxy(handle)
