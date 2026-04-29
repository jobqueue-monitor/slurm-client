from typing import Any

import httpx
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Header, TabbedContent, TabPane

from slurm_client.rest_api import (
    api_version,
    jobs_summary,
    nodes_summary,
    partitions_summary,
    ping,
)
from slurm_client.rest_api.connection import connect, refresh_token
from slurm_client.rest_api.request import Request
from slurm_client.rest_api.table_message import TableContentFetched
from slurm_client.screens.error import ErrorScreen, NetworkError
from slurm_client.screens.sort import SortScreen
from slurm_client.widgets.footer import SlurmClientFooter


class SlurmClient(App):
    TITLE = "jobqueue-monitor"
    CSS_PATH = "app.tcss"

    COLUMN_NAMES = {
        "partitions": ["name", "total_nodes", "total_cpus", "state"],
        "jobs": ["name", "user", "group", "partition", "start_time", "state"],
        "nodes": ["name", "address", "hostname", "state", "partitions"],
    }

    BINDINGS = {
        Binding("left", "previous_tab", "Previous tab", show=False),
        Binding("right", "next_tab", "Next tab", show=False),
    }

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.ssh_con = None
        self.socks_proxy = None
        self.api_con = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="content"):
            with Horizontal(id="actions"):
                with Horizontal():
                    yield Button("Sort", id="sort")
                    yield Button("Filters", id="filters")
            with TabbedContent(id="tabs"):
                with TabPane("Partitions", id="partitions", classes="tab"):
                    yield DataTable(id="partitions")
                with TabPane("Jobs", id="jobs", classes="tab"):
                    yield DataTable(id="jobs")
                with TabPane("Nodes", id="nodes", classes="tab"):
                    yield DataTable(id="nodes")
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

    async def on_mount(self) -> None:
        self.run_worker(self.setup_connections(), exclusive=True)

        partitions_table = self.query_one("DataTable#partitions")
        for col in self.COLUMN_NAMES["partitions"]:
            partitions_table.add_column(col, key=col)
        self.sort_column = self.COLUMN_NAMES["partitions"][0]
        partitions_table.cursor_type = "row"
        partitions_table.zebra_stripes = True

        jobs_table = self.query_one("DataTable#jobs")
        for col in self.COLUMN_NAMES["jobs"]:
            jobs_table.add_column(col, key=col)
        jobs_table.cursor_type = "row"
        jobs_table.zebra_stripes = True

        nodes_table = self.query_one("DataTable#nodes")
        for col in self.COLUMN_NAMES["nodes"]:
            nodes_table.add_column(col, key=col)
        nodes_table.cursor_type = "row"
        nodes_table.zebra_stripes = True

        self.set_interval(self.config.ping_interval, self.ping)
        self.set_interval(self.config.ping_interval, self._refresh_current_table)

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, msg: TabbedContent.TabActivated) -> None:
        active = msg.pane.id
        table = self.query_one(f"DataTable#{active}")
        self.sort_column = self.COLUMN_NAMES[active][0]
        table.sort(self.sort_column)
        table.focus()

        self.run_worker(self._refresh_current_table())

    def action_previous_tab(self) -> None:
        tabs = self.query_one("Tabs")
        tabs.action_previous_tab()

    def action_next_tab(self) -> None:
        tabs = self.query_one("Tabs")
        tabs.action_next_tab()

    async def _refresh_current_table(self) -> None:
        if self.con is None:
            return

        tabs = self.query_one(TabbedContent)
        await self._fetch_table_data(tabs.active)

    async def _fetch_table_data(self, kind: str) -> None:
        requests = {
            "partitions": partitions_summary,
            "jobs": jobs_summary,
            "nodes": nodes_summary,
        }
        request = requests[kind]
        r = await self.query_api(request)
        msg = request.response_parser(r.json())
        self.post_message(msg)

    @on(TableContentFetched)
    def on_table_content_fetched(self, msg: TableContentFetched):
        table = self.query_one(f"DataTable#{msg.kind}")

        focused = table.has_focus
        pos = table.cursor_coordinate
        scroll_y = table.scroll_y

        table.clear()
        for row in msg.rows():
            table.add_row(*row)
        table.sort(self.sort_column)

        table.cursor_coordinate = pos
        table.scroll_y = scroll_y
        if focused:
            table.focus()

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "sort":
                tabs = self.query_one("TabbedContent")
                active = tabs.active
                sort_column = await self.push_screen_wait(
                    SortScreen(self.COLUMN_NAMES[active])
                )
                if sort_column is None:
                    return

                table = self.query_one(f"DataTable#{active}")
                table.sort(sort_column)
                self.sort_column = sort_column

    async def ping(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return

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
