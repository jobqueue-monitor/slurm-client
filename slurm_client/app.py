from typing import Any

import httpx
from textual.app import App, ComposeResult
from textual.widgets import Header

from slurm_client.api import api_version, ping
from slurm_client.api.connection import connect, create_socks_proxy, refresh_token
from slurm_client.rest_api.request import Request
from slurm_client.widgets.footer import SlurmClientFooter


class SlurmClient(App):
    TITLE = "jobqueue-monitor"
    CSS_PATH = "app.tcss"

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.ssh_con = None
        self.socks_proxy = None
        self.api_con = None

    def compose(self) -> ComposeResult:
        yield Header()

        yield SlurmClientFooter()

    async def determine_api_version(self):
        response = await self.query_api(api_version)

        if response.status_code != httpx.codes.OK:
            return None

        self.post_message(api_version.response_parser(response.json()))

    async def setup_connections(self) -> None:
        self.ssh_con = await connect(self.config.server)
        self.socks_proxy = await create_socks_proxy(self.ssh_con)
        self.api_con = httpx.AsyncClient()  # proxy=self.socks_proxy.to_url())

        await self.determine_api_version()
        await self.ping()

    async def on_load(self) -> None:
        self.token = None
        self.api_version = None

        self.run_worker(self.setup_connections(), exclusive=True)

    async def on_mount(self) -> None:
        self.set_interval(self.config.ping_interval, self.ping)

    async def ping(self) -> str:
        r = await self.query_api(request=ping)
        if r.status_code != httpx.codes.OK:
            server_info = {}
        else:
            server_info = r.json()

        footer = self.screen.query_one(SlurmClientFooter)
        footer.post_message(ping.response_parser(server_info))

    async def query_api(
        self,
        request: Request,
    ) -> dict[str, Any]:
        path = request.path.format(
            version=self.api_version if self.api_version is not None else ""
        )

        if self.token is None or not self.token.is_valid():
            self.token = await refresh_token(
                self.ssh_con, lifespan=self.config.token_lifespan
            )

        url = f"{self.config.address}/{path.lstrip('/')}"

        fetch = getattr(self.api_con, request.method, None)
        if fetch is None:
            raise ValueError(f"invalid method: {request.method}")

        return await fetch(
            url,
            params=request.parameters,
            headers={"X-SLURM-USER-TOKEN": str(self.token)},
        )

    async def on_unmount(self) -> None:
        # close all connections
        if self.api_con:
            await self.api_con.aclose()
        if self.socks_proxy:
            await self.socks_proxy.close()
        if self.ssh_con:
            await self.ssh_con.close()
