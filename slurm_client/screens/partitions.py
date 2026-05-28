import httpx
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ItemGrid, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label, ListItem, ListView, Static

from slurm_client.rest_api.nodes import node_details
from slurm_client.rest_api.partitions import (
    PartitionDetails,
    ResourcesDict,
    partition_details,
    resource_usage,
)
from slurm_client.rest_api.resources import split_value
from slurm_client.screens.error import ErrorScreen, NetworkError
from slurm_client.widgets.footer import SlurmClientFooter
from slurm_client.widgets.resource import ResourceBar


def _render_resource(name: str, total: str, used: str | None) -> ResourceBar:
    total_value, total_units = split_value(total)
    used_value, used_units = split_value(used)

    if total_units != used_units and used not in ("", None):
        raise ValueError(f"mismatching units ({total_units} != {used_units}")

    return ResourceBar(used=used_value, total=total_value, units=total_units)


def _render_resources(
    resources: ResourcesDict, exclude: set[str]
) -> dict[str, ResourceBar]:
    total = resources["total"]
    used = resources["used"]

    return {
        name: _render_resource(name, total[name], used.get(name))
        for name in total
        if name not in exclude
    }


node_columns = ["name", "address", "state"]


class PartitionDetails(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("Ctrl+g", "refresh", "Refresh"),
    ]
    CSS_PATH = "partitions.tcss"

    def __init__(self, partition_name: str, **kwargs):
        super().__init__(**kwargs)

        self.partition_name = partition_name

        self.resource_widgets = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Label("Partition", id="title")
        yield Static(id="alternate")

        with Vertical():
            yield ListView(id="states", classes="details")
            yield ItemGrid(id="tres", regular=True)
            yield DataTable(id="nodes", classes="details")

        yield SlurmClientFooter()

    def on_mount(self) -> None:
        states = self.query_one("ListView#states")
        states.border_title = "States"

        resources = self.query_one("#tres")
        resources.border_title = "Tracked resources"

        nodes = self.query_one("DataTable#nodes")
        nodes.border_title = "Nodes"
        nodes.add_columns(*node_columns)

        self.run_worker(self.fetch_partition_details())
        self.run_worker(self.app.ping())

    async def fetch_partition_details(self):
        request = partition_details.path_parameters(partition_name=self.partition_name)
        r = await self.app.query_api(request)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return

        msg = request.response_parser(r.json())

        request = resource_usage.parser_parameters(partition=self.partition_name)
        r = await self.app.query_api(request)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return
        msg.tracked_resources["used"] = request.response_parser(r.json())

        r = await self.app.query_api(node_details)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return

        msg.nodes = node_details.response_parser(r.json(), msg.nodes)

        self.post_message(msg)

    @on(PartitionDetails)
    async def display_partition_details(self, msg: PartitionDetails) -> None:
        title = self.query_one("Label#title")
        title.update(f"[b]Partition[/b]: {msg.name}")

        alternate_field = self.query_one("Static#alternate")
        alternate_field.update(msg.alternate)

        states = self.query_one("ListView#states")
        states.clear()
        states.extend([ListItem(Label(state.lower())) for state in msg.states])

        if self.resource_widgets is None:
            self.resource_widgets = _render_resources(
                msg.tracked_resources, exclude={"billing"}
            )
            resources = self.query_one("#tres")
            for name, widget in self.resource_widgets.items():
                id_ = f"{name.replace(':', '_').replace('/', '_')}_label"
                resources.mount(Label(name, id=id_))
                resources.mount(widget)
        else:
            for name, value in msg.tracked_resources["used"].items():
                widget = self.resource_widgets[name]
                widget.used = value

        nodes = self.query_one("DataTable#nodes")
        nodes.clear()
        for row in msg.nodes:
            filtered = [v for k, v in row.items() if k in node_columns]
            nodes.add_row(*filtered)

    async def action_refresh(self) -> None:
        await self.fetch_partition_details()

    @on(NetworkError)
    async def on_network_error(self, msg: NetworkError) -> None:
        r = msg.response
        error_message = (
            f"[b]Network error[/b]: {r.status_code}. To try again refresh the table."
        )
        self.app.push_screen(ErrorScreen(error_message))
