from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, TabbedContent, TabPane

from slurm_client.rest_api import (
    jobs_summary,
    nodes_summary,
    partitions_summary,
)
from slurm_client.rest_api.table_message import TableContentFetched
from slurm_client.screens.partitions import PartitionDetails
from slurm_client.screens.sort import SortScreen
from slurm_client.widgets.footer import SlurmClientFooter


class MainScreen(Screen):
    CSS_PATH = "main.tcss"

    COLUMN_NAMES = {
        "partitions": ["name", "total_nodes", "total_cpus", "state"],
        "jobs": ["name", "user", "group", "partition", "start_time", "state"],
        "nodes": ["name", "address", "hostname", "state", "partitions"],
    }

    BINDINGS = {
        Binding("left", "previous_tab", "Previous tab", show=False),
        Binding("right", "next_tab", "Next tab", show=False),
    }

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

    async def on_mount(self) -> None:
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

        self.app.timers["main:table_refresh"] = self.app.set_interval(
            self.app.config.ping_interval, self._refresh_current_table
        )

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

    def current_tab(self) -> str:
        tabs = self.query_one("TabbedContent")
        return tabs.active

    async def _refresh_current_table(self) -> None:
        if self.app.con is None:
            return

        active_tab = self.current_tab()
        await self._fetch_table_data(active_tab)

    async def _fetch_table_data(self, kind: str) -> None:
        requests = {
            "partitions": partitions_summary,
            "jobs": jobs_summary,
            "nodes": nodes_summary,
        }
        request = requests[kind]
        r = await self.app.query_api(request)
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

    async def on_data_table_row_selected(self, msg: DataTable.RowSelected) -> None:
        active_tab = self.current_tab()
        active_table = self.query_one(f"DataTable#{active_tab}")
        row = active_table.get_row_at(msg.cursor_row)

        name = row[0]
        match active_tab:
            case "partitions":
                self.app.push_screen(PartitionDetails(name))
            case _:
                # not yet implemented
                return

    @on(ScreenSuspend)
    def on_screen_suspend(self) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("main:"):
                continue
            timer.pause()

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenResume) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("main:"):
                continue
            timer.resume()
