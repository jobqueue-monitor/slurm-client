from dataclasses import dataclass
from typing import Any

import httpx
from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label

from slurm_client.screens.error import ErrorScreen, NetworkError
from slurm_client.widgets.footer import SlurmClientFooter


class PartitionsSummary(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("Ctrl+g", "refresh", "Refresh"),
    ]
    CSS_PATH = "partitions.tcss"

    ROW_NAMES = ["name", "total_nodes", "total_cpus", "state"]

    @dataclass
    class PartitionsFetched(Message):
        partitions: list[dict[str, Any]]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Partitions", id="title")
        yield DataTable()
        yield SlurmClientFooter()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(*self.ROW_NAMES)

        self.run_worker(self.fetch_partitions)

    async def fetch_partitions(self):
        r = await self.app.query_api(method="GET", path="/slurm/{version}/partitions")
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return

        partitions = r.json()["partitions"]
        self.post_message(self.PartitionsFetched(partitions))

    @on(PartitionsFetched)
    async def display_partitions_summary(self, msg: PartitionsFetched) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for partition in msg.partitions:
            entry = {
                "name": partition["name"],
                "total_nodes": partition["nodes"]["total"],
                "total_cpus": partition["cpus"]["total"],
                "state": partition["partition"]["state"][0],
            }
            table.add_row(*entry.values())

    async def action_refresh(self) -> None:
        await self.fetch_partitions()

    @on(NetworkError)
    async def on_network_error(self, msg: NetworkError) -> None:
        r = msg.response
        error_message = (
            f"[b]Network error[/b]: {r.status_code}. To try again refresh the table."
        )
        self.app.push_screen(ErrorScreen(error_message))
