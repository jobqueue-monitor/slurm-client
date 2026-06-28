import httpx
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ItemGrid, Vertical
from textual.screen import Screen
from textual.widgets import Header, Label, ListItem, ListView, Static

from slurm_client.errors import NetworkError, TokenError
from slurm_client.messages import FailedRequest, FailedTokenCreation
from slurm_client.rest_api.errors import format_error_response
from slurm_client.rest_api.nodes import all_nodes
from slurm_client.rest_api.partitions import (
    PartitionDetails,
    partition_details,
    resource_usage,
)
from slurm_client.screens.error import ErrorScreen
from slurm_client.screens.nodes import NodeDetails
from slurm_client.widgets.footer import SlurmClientFooter
from slurm_client.widgets.resource import render_resources
from slurm_client.widgets.table import SortableTable

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
            yield SortableTable(node_columns, id="nodes", classes="details")

        yield SlurmClientFooter()

    def on_mount(self) -> None:
        states = self.query_one("ListView#states")
        states.border_title = "States"

        resources = self.query_one("#tres")
        resources.border_title = "Tracked resources"

        nodes = self.query_one("SortableTable#nodes")
        nodes.border_title = "Nodes"
        nodes.cursor_type = "row"
        nodes.zebra_stripes = True

        self.run_worker(self.fetch_partition_details())
        self.run_worker(self.app.ping())

    async def fetch_partition_details(self):
        request = partition_details.path_parameters(partition_name=self.partition_name)
        try:
            r = await self.app.query_api(request)
        except TokenError as e:
            self.post_message(FailedTokenCreation(str(e)))
            return
        except NetworkError as e:
            self.post_message(FailedRequest(str(e)))
            return

        if r.status_code != httpx.codes.OK:
            reason = format_error_response(r)
            self.post_message(FailedRequest(reason))
            return
        if r.status_code != httpx.codes.OK:
            reason = format_error_response(r)
            self.post_message(FailedRequest(reason))
            return

        msg = request.response_parser(r.json())

        request = resource_usage.parser_parameters(partition=self.partition_name)
        r = await self.app.query_api(request)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return
        msg.tracked_resources["used"] = request.response_parser(r.json())

        r = await self.app.query_api(all_nodes)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return

        msg.nodes = [
            node
            for node in all_nodes.response_parser(r.json())
            if node.name in msg.nodes
        ]

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
            self.resource_widgets = render_resources(
                msg.tracked_resources, exclude={"billing"}, units={"memory": "M"}
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

        nodes = self.query_one("SortableTable#nodes")
        filtered_rows = [
            [getattr(node_details, col) for col in node_columns]
            for node_details in msg.nodes
        ]
        nodes.replace_contents(filtered_rows)

    async def action_refresh(self) -> None:
        await self.fetch_partition_details()

    async def on_data_table_row_selected(self, msg: SortableTable.RowSelected) -> None:
        table = msg.data_table
        if not isinstance(table, SortableTable) or table.id != "nodes":
            return

        row = table.get_row_at(msg.cursor_row)

        name = row[0]
        self.app.push_screen(NodeDetails(name))

    @on(NetworkError)
    async def on_network_error(self, msg: NetworkError) -> None:
        r = msg.response
        error_message = (
            f"[b]Network error[/b]: {r.status_code}. To try again refresh the table."
        )
        self.app.push_screen(ErrorScreen(error_message))
