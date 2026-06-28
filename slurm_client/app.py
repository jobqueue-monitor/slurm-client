import asyncio
from typing import Any

import httpx2
from textual import on
from textual.app import App
from textual.messages import ExitApp
from textual.screen import ModalScreen

from slurm_client.errors import ConnectionError, NetworkError
from slurm_client.messages import (
    ConnectionEstablished,
    FailedRequest,
    FailedSSHConnection,
    FatalError,
)
from slurm_client.rest_api import (
    api_version,
    ping,
)
from slurm_client.rest_api.connection import connect, refresh_token
from slurm_client.rest_api.request import Request
from slurm_client.screens.error import ErrorScreen, FatalErrorScreen
from slurm_client.screens.main import MainScreen
from slurm_client.widgets.footer import SlurmClientFooter


class SlurmClient(App):
    TITLE = "jobqueue-monitor"

    SCREENS = {"main": MainScreen}

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.timers = {}

    async def determine_api_version(self):
        r = await self.query_api(api_version)
        if r.status_code != httpx2.codes.OK:
            raise NetworkError(r)

        self.api_version = api_version.response_parser(r.json())

    async def setup_connections(self) -> None:
        widget = self.screen.query_one("#content")
        widget.loading = True

        try:
            self.con = await connect(self.config.server)
        except ConnectionError as e:
            self.post_message(FailedSSHConnection(str(e)))
            return

        try:
            await self.determine_api_version()
        except NetworkError as e:
            self.post_message(FailedRequest(str(e)))
            return

        widget.loading = False

        self.post_message(ConnectionEstablished())

    @on(ConnectionEstablished)
    def on_connection_established(self, msg: ConnectionEstablished):
        self.app.timers["ping"] = self.app.set_interval(
            self.config.ping_interval, self.ping
        )
        self.ping()

    async def on_load(self) -> None:
        self.con = None
        self.token = None
        self.api_version = None

    async def on_mount(self) -> None:
        self.push_screen("main")
        self.run_worker(self.setup_connections, exclusive=True)

    async def ping(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return

        r = await self.query_api(request=ping)
        if r.status_code != httpx2.codes.OK:
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

        try:
            return await fetch(url, params=request.parameters, headers=headers)
        except httpx2.ReadTimeout as e:
            reason = f"Failed to fetch {url}: read timeout"
            raise NetworkError(reason) from e

    def stop_all_timers(self) -> None:
        for timer in self.timers.values():
            timer.stop()

    @on(FailedRequest)
    def on_failed_request(self, msg: FailedRequest):
        self.push_screen(ErrorScreen(msg.reason))

    @on(FatalError)
    async def on_fatal_error(self, msg: FatalError):
        error = msg.render()

        self.stop_all_timers()

        def check_quit(quit: bool | None) -> None:
            self.exit(1)

        self.push_screen(FatalErrorScreen(error), check_quit)

    @on(ExitApp)
    async def on_exit(self) -> None:
        self.stop_all_timers()

        for task in asyncio.all_tasks():
            task.cancel()

        # disconnect
        if self.con:
            await self.con.close()
