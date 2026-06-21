from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import httpx
from textual import on
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume, ScreenSuspend
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Header, Label, TabbedContent, TabPane

from slurm_client.rest_api.jobs import Job, job_details
from slurm_client.rest_api.nodes import all_nodes
from slurm_client.screens.error import NetworkError
from slurm_client.widgets.footer import SlurmClientFooter
from slurm_client.widgets.kvgrid import KeyValueGrid
from slurm_client.widgets.table import SortableTable

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from textual.app import ComposeResult

    from slurm_client.rest_api.nodes import NodeDetails


def render(name: str, value: Any) -> str:
    if value is None:
        return "n/a"

    match value:
        case str():
            return cast(str, value)
        case int():
            return str(value)
        case dt.datetime():
            if value.timestamp() == 0:
                return "n/a"
            else:
                return value.isoformat()
        case _:
            return str(value)


def render_exit_code(exit_code: dict[str, Any], state: list[str]) -> str:
    if state[0] in ["PENDING", "RUNNING"]:
        return "n/a"

    msg = f"{exit_code['status'][0]} ({exit_code['return_code']})"
    if (signal := exit_code["signal"]) and signal["id"] is not None:
        return " ".join([msg, f"Signal received: {signal['name']} ({signal['id']})"])

    return msg


@dataclass
class JobDetailsFetched(Message):
    details: Job

    excluded_nodes: list[NodeDetails] | None = None
    required_nodes: list[NodeDetails] | None = None
    scheduled_nodes: list[NodeDetails] | None = None


class JobDetails(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("Ctrl+g", "refresh", "Refresh"),
    ]
    CSS_PATH = "jobs.tcss"

    node_columns: ClassVar[list[str]] = ["name", "address", "state"]

    def __init__(self, job_id: int, **kwargs):
        super().__init__(**kwargs)

        self.job_id = job_id

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            yield Label(id="title")

        with TabbedContent(id="tabs"):
            with TabPane("Details", classes="tab"):
                yield KeyValueGrid(id="details")
            with TabPane("Status", classes="tab"):
                yield KeyValueGrid(id="status", classes="status-grid")
                yield KeyValueGrid(id="status-times", classes="status-grid")
                yield KeyValueGrid(id="logs", classes="status-grid")
            with TabPane("Submission", classes="tab"):
                yield KeyValueGrid(id="submission")
            with TabPane("Scheduling", classes="tab"):
                yield KeyValueGrid(id="scheduling-info")
                with Vertical(id="nodes"):
                    yield SortableTable(
                        self.node_columns, id="excluded-nodes", classes="nodes"
                    )
                    yield SortableTable(
                        self.node_columns, id="required-nodes", classes="nodes"
                    )
                    yield SortableTable(
                        self.node_columns, id="scheduled-nodes", classes="nodes"
                    )
            with TabPane("Resources", classes="tab"):
                yield SortableTable(["name"])

        yield SlurmClientFooter()

    def on_mount(self):
        self.run_worker(self.app.ping())
        self.run_worker(self.fetch_job_details())

        status = self.query_one("#status")
        status.border_title = "State"

        status_times = self.query_one("#status-times")
        status_times.border_title = "Times"

        logs = self.query_one("#logs")
        logs.border_title = "Standard streams"

        nodes = self.query_one("#nodes")
        nodes.border_title = "Nodes"
        nodes_tables = self.query(".nodes")
        for title, table in zip(
            ["Excluded nodes", "Required nodes", "Scheduled nodes"], nodes_tables
        ):
            table.border_title = title

    async def fetch_job_details(self) -> None:
        request = job_details.path_parameters(job_id=self.job_id)

        r = await self.app.query_api(request)
        if r.status_code != httpx.codes.OK:
            raise ValueError(f"response: {r.status_code}")
            self.post_message(NetworkError(r))
            return

        parsed = request.response_parser(r.json())
        msg = JobDetailsFetched(parsed)

        r = await self.app.query_api(all_nodes)
        if r.status_code != httpx.codes.OK:
            self.post_message(NetworkError(r))
            return

        nodes = all_nodes.response_parser(r.json())
        msg.excluded_nodes = [
            node for node in nodes if node.name in parsed.scheduling.excluded_nodes
        ]
        msg.required_nodes = [
            node for node in nodes if node.name in parsed.scheduling.required_nodes
        ]
        msg.scheduled_nodes = [
            node for node in nodes if node.name in parsed.scheduling.scheduled_nodes
        ]

        self.post_message(msg)

    @on(JobDetailsFetched)
    async def display_job_details(self, msg: JobDetailsFetched) -> None:
        job = msg.details
        title = self.query_one("Label#title")
        title.update(f"[b]Job[/b]: {job.info.name}")

        details = self.query_one("#details")
        for key, value in job.info.render().items():
            value_id = f"job-details-value-{key.replace(' ', '_')}"
            rendered = render(key, value)
            details.upsert(key, rendered, value_id)

        rendered_status = job.status.render()
        status = self.query_one("#status")
        status.upsert_many(
            {
                key: (
                    render(key, value)
                    if "exit_code" not in key
                    else render_exit_code(value, job.status.state)
                )
                for key, value in rendered_status["status"].items()
            },
            id_template="job-status-value-{key}",
        )

        times = self.query_one("#status-times")
        times.upsert_many(
            {
                key: render(key, value)
                for key, value in rendered_status["times"].items()
            },
            id_template="job-status-times-value-{key}",
        )

        logs = self.query_one("#logs")
        logs.upsert_many(
            {key: render(key, value) for key, value in rendered_status["logs"].items()},
            id_template="job-logs-value-{key}",
        )

        submission_tab = self.query_one("#submission")
        submission_tab.upsert_many(
            {key: render(key, value) for key, value in job.submission.render().items()},
            id_template="job-submission-value-{key}",
        )

        scheduling_info = self.query_one("#scheduling-info")
        scheduling_info.upsert_many(
            {key: render(key, value) for key, value in job.scheduling.render().items()},
            id_template="job-scheduling-value-{key}",
        )
        excluded_nodes_table = self.query_one("#excluded-nodes")
        excluded_nodes_table.replace_contents(
            [list(node.summary().values()) for node in msg.excluded_nodes]
        )
        required_nodes_table = self.query_one("#required-nodes")
        required_nodes_table.replace_contents(
            [list(node.summary().values()) for node in msg.required_nodes]
        )
        scheduled_nodes_table = self.query_one("#scheduled-nodes")
        scheduled_nodes_table.replace_contents(
            [list(node.summary().values()) for node in msg.scheduled_nodes]
        )

    @on(ScreenSuspend)
    def on_screen_suspend(self) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("job:"):
                continue
            timer.pause()

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenResume) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("job:"):
                continue
            timer.resume()
