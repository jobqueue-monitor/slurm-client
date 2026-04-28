from typing import Any

import httpx
from textual.app import App, ComposeResult
from textual.widgets import Header

from slurm_client.rest_api import api_version, ping
from slurm_client.rest_api.connection import connect, refresh_token
from slurm_client.rest_api.request import Request
from slurm_client.screens.error import ErrorScreen, NetworkError
from slurm_client.screens.partitions import PartitionsSummary
from slurm_client.widgets.footer import SlurmClientFooter


class SlurmClient(App):
    TITLE = "jobqueue-monitor"
    CSS_PATH = "app.tcss"

    SCREENS = {
        "partitions_summary": PartitionsSummary,
    }
    BINDINGS = [("p", "push_screen('partitions_summary')", "Partitions")]

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
        r = await self.query_api(api_version)
        if r.status_code != httpx.codes.OK:
            self.screen.post_message(NetworkError(r))
            return

        self.api_version = api_version.response_parser(r.json())

    async def setup_connections(self) -> None:
        self.con = await connect(self.config.server)

        await self.determine_api_version()
        await self.ping()

    async def on_load(self) -> None:
        self.con = None
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
                self.con.ssh, lifespan=self.config.token_lifespan
            )

        url = f"{self.config.address}/{path.lstrip('/')}"

        fetch = getattr(self.con.api, request.method, None)
        if fetch is None:
            raise ValueError(f"invalid method: {request.method}")

        headers = {}
        if self.token is not None:
            headers["X-SLURM-USER-TOKEN"] = str(self.token)

        return await fetch(url, params=request.parameters, headers=headers)

    def on_networkerror(self, msg: NetworkError):
        r = msg.response
        error = (
            f"Network error while fetching {r.url}: {r.status_code} ({r.reason_phrase})"
        )
        self.push_screen(ErrorScreen(error))

    async def on_unmount(self) -> None:
        # disconnect
        if self.con:
            await self.con.close()
