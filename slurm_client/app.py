from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Footer, Header, Label

from slurm_client.connection import connect, create_socks_proxy, refresh_token


def extract_api_version(api_paths: dict[str, Any]) -> str:
    versions = {
        path.lstrip("/").split("/")[1]
        for path in api_paths["paths"]
        if path.startswith("/slurm")
    }

    return max(versions)


def process_ping_response(result: dict[str, Any]) -> dict[str, Any]:
    if "pings" not in result or len(result["pings"]) == 0:
        return None

    p = result["pings"][0]
    slurm_version = result["meta"]["slurm"]["release"]

    return {"server": p["hostname"], "latency": p["latency"], "version": slurm_version}


class SlurmClient(App):
    TITLE = "jobqueue-monitor"
    CSS_PATH = "app.tcss"

    @dataclass
    class PingMessage(Message):
        server: str
        latency: float
        version: str

        def items(self):
            yield from asdict(self).items()

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.ssh_con = None
        self.socks_proxy = None
        self.api_con = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="footer-area"):
            with Horizontal(id="footer-inner"):
                yield Footer()
            yield Label(id="server-info")

    async def determine_api_version(self):
        response = await self.query_api(method="GET", path="/openapi/v3")

        if response.status_code != httpx.codes.OK:
            return None

        return extract_api_version(response.json())

    async def setup_connections(self) -> None:
        self.ssh_con = await connect(self.config.server)
        self.socks_proxy = await create_socks_proxy(self.ssh_con)
        self.api_con = httpx.AsyncClient()  # proxy=self.socks_proxy.to_url())

        self.api_version = await self.determine_api_version()

        await self.ping()

    async def on_load(self) -> None:
        self.run_worker(self.setup_connections, exclusive=True)

        self.token = None
        self.api_version = None

    async def on_mount(self) -> None:
        self.set_interval(self.config.ping_interval, self.ping)

    async def ping(self) -> str:
        r = await self.query_api(method="GET", path="/slurm/{version}/ping")
        if r.status_code != httpx.codes.OK:
            server_info = None
        else:
            server_info = process_ping_response(r.json())

        if server_info is None:
            server_info = {
                "server": "unknown",
                "latency": float("nan"),
                "version": "n/a",
            }

        self.post_message(self.PingMessage(**server_info))

    @on(PingMessage)
    async def display_ping(self, message: PingMessage):
        formatters = {
            "latency": lambda x: f"{x / 1000:.3f} ms",
        }
        translations = {
            "server": "name",
        }

        translated = {
            translations.get(key, key): formatters.get(key, lambda x: x)(value)
            for key, value in message.items()
        }

        formatted = "[b]server[/b]: " + " | ".join(
            [f"[b]{k}[/b]: {v}" for k, v in translated.items()]
        )

        label = self.query_one("Label#server-info")
        label.update(formatted)

    async def query_api(
        self,
        method: Literal["GET", "POST"],
        path: str,
        parameters: dict[str, Any] = None,
    ) -> dict[str, Any]:
        if "{version}" in path:
            # fill in the api version
            path = path.format(version=self.api_version)

        if parameters is None:
            parameters = {}

        if self.token is None or not self.token.is_valid():
            self.token = await refresh_token(
                self.ssh_con, lifespan=self.config.token_lifespan
            )

        url = f"{self.config.address}/{path.lstrip('/')}"

        methods = {
            "POST": self.api_con.post,
            "GET": self.api_con.get,
        }
        fetch = methods.get(method)
        if fetch is None:
            raise ValueError(f"invalid method: {method}")

        return await fetch(
            url, params=parameters, headers={"X-SLURM-USER-TOKEN": str(self.token)}
        )

    async def on_unmount(self) -> None:
        # close all connections
        if self.api_con:
            await self.api_con.aclose()
        if self.socks_proxy:
            await self.socks_proxy.close()
        if self.ssh_con:
            await self.ssh_con.close()
