from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ItemGrid
from textual.events import ScreenResume, ScreenSuspend
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Header, Label, TabbedContent, TabPane

from slurm_client.rest_api.jobs import Job, job_details
from slurm_client.screens.error import NetworkError
from slurm_client.widgets.footer import SlurmClientFooter
from slurm_client.widgets.table import SortableTable


def render(name: str, value: Any) -> str:
    if value is None:
        return "n/a"

    match name:
        case "":
            return "something"

    match value:
        case str():
            return cast(str, value)
        case int():
            return str(value)
        case _:
            return str(value)


@dataclass
class JobDetailsFetched(Message):
    details: Job


class JobDetails(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("Ctrl+g", "refresh", "Refresh"),
    ]
    CSS_PATH = "jobs.tcss"

    def __init__(self, job_id: int, **kwargs):
        super().__init__(**kwargs)

        self.job_id = job_id

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            yield Label(id="title")

        with TabbedContent(id="tabs"):
            with TabPane("Details", classes="tab"):
                yield ItemGrid(id="details")
            with TabPane("Status", classes="tab"):
                yield SortableTable(["name"])
            with TabPane("Submission", classes="tab"):
                yield SortableTable(["name"])
            with TabPane("Scheduling", classes="tab"):
                yield SortableTable(["name"])
            with TabPane("Resources", classes="tab"):
                yield SortableTable(["name"])

        yield SlurmClientFooter()

    def on_mount(self):
        self.run_worker(self.app.ping())
        self.run_worker(self.fetch_job_details())

    async def fetch_job_details(self) -> None:
        request = job_details.path_parameters(job_id=self.job_id)

        r = await self.app.query_api(request)
        if r.status_code != httpx.codes.OK:
            raise ValueError(f"response: {r.status_code}")
            self.post_message(NetworkError(r))
            return

        parsed = request.response_parser(r.json())
        msg = JobDetailsFetched(parsed)

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
            if labels := details.query(f"Label#{value_id}"):
                value_label = labels[0]
                value_label.update(rendered)
                continue

            key_label = Label(f"[b]{key}[/b]", classes="key-column")
            value_label = Label(rendered, id=value_id)
            details.mount(key_label)
            details.mount(value_label)

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
