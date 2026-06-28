import datetime as dt
from dataclasses import dataclass
from typing import Any, cast

import httpx
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ItemGrid
from textual.events import ScreenResume, ScreenSuspend
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Header, Label
from textual_plotext import PlotextPlot

from slurm_client.errors import NetworkError, TokenError
from slurm_client.messages import FailedRequest, FailedTokenCreation
from slurm_client.rest_api.nodes import NodeDetails, node_details
from slurm_client.rest_api.resources import as_unit
from slurm_client.widgets.footer import SlurmClientFooter
from slurm_client.widgets.resource import render_resource


@dataclass
class NodeDetailsFetched(Message):
    details: NodeDetails


def render_state(states: list[str]) -> str:
    return ", ".join(states)


def render_reason(r: dict[str, Any]) -> str:
    return f"{r['reason']} (changed by {r['set_by_user']} at {r['changed_at']:%Y-%m-%d %H:%M:%S})"


def render(name: str, value: Any) -> str:
    if value is None:
        return "n/a"
    match name:
        case "boot_time" | "last_busy":
            return value.isoformat()
        case "partitions":
            return ", ".join(value)
        case "state":
            return render_state(value)
        case "reason":
            return render_reason(value)

    match value:
        case str():
            return cast(str, value)
        case int():
            return str(value)
        case _:
            return str(value)


date_pattern = "Y-m-d H:M:S"
date_format = "".join(f"%{char}" if char.isalpha() else char for char in date_pattern)


class NodeDetails(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("Ctrl+g", "refresh", "Refresh"),
    ]

    CSS_PATH = "nodes.tcss"

    def __init__(self, node_name: str, *, max_data_points: int = 200, **kwargs):
        super().__init__(**kwargs)

        self.node_name = node_name
        self.max_data_points = max_data_points

        self.time = []
        self.cpu_load = []
        self.used_memory = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            yield Label("Node", id="title")

        with Container(classes="details"):
            yield ItemGrid(id="node-info")
            yield ItemGrid(id="node-status")
            yield ItemGrid(id="resources")

        with Horizontal(id="live-usage"):
            yield PlotextPlot(id="live-cpu", classes="plot")
            yield PlotextPlot(id="live-mem", classes="plot")

        yield SlurmClientFooter()

    def on_mount(self):
        node_info = self.query_one("ItemGrid#node-info")
        node_info.border_title = "Details"

        node_status = self.query_one("ItemGrid#node-status")
        node_status.border_title = "Status"

        resources = self.query_one("#resources")
        resources.border_title = "Resources"

        live_usage = self.query_one("#live-usage")
        live_usage.border_title = "Live Resource Usage"

        live_cpu = self.query_one("PlotextPlot#live-cpu")
        live_cpu.plt.xlabel("time (UTC)")
        live_cpu.plt.title("CPU load (%)")

        live_mem = self.query_one("PlotextPlot#live-mem")
        live_mem.plt.xlabel("time (UTC)")
        live_mem.plt.title("Used memory (MB)")

        self.run_worker(self.app.ping())
        self.app.timers["node:details"] = self.app.set_interval(
            self.app.config.ping_interval, self.fetch_node_details
        )

    @on(ScreenSuspend)
    def on_screen_suspend(self) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("node:"):
                continue
            timer.pause()

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenResume) -> None:
        for name, timer in self.app.timers.items():
            if not name.startswith("node:"):
                continue
            timer.resume()

    async def fetch_node_details(self):
        request = node_details.path_parameters(node_name=self.node_name)
        try:
            r = await self.app.query_api(request)
        except TokenError as e:
            self.post_message(FailedTokenCreation(str(e)))
            return
        except NetworkError as e:
            self.post_message(FailedRequest(str(e)))
            return

        if r.status_code != httpx.codes.OK:
            self.post_message(FailedRequest(r))
            return

        parsed = request.response_parser(r.json())
        msg = NodeDetailsFetched(parsed)

        self.post_message(msg)

    def push_data(
        self, time: dt.datetime, cpu_load: int | None, used_memory: int | None
    ):
        if len(self.time) >= self.max_data_points:
            self.time.pop(0)
            self.cpu_load.pop(0)
            self.used_memory.pop(0)

        self.time.append(time)
        self.cpu_load.append(cpu_load)
        self.used_memory.append(used_memory)

    @on(NodeDetailsFetched)
    async def display_node_details(self, msg: NodeDetailsFetched) -> None:
        details = msg.details

        title = self.query_one("Label#title")
        title.update(f"[b]Node[/b]: {details.name}")

        node_info = self.query_one("#node-info")
        for key, value in details.render_info().items():
            value_id = f"node-info-value-{key}"
            if labels := node_info.query(f"Label#{value_id}"):
                value_label = labels[0]
                value_label.update(render(key, value))
                continue

            key_label = Label(f"[b]{key}[/b]")
            value_label = Label(render(key, value), id=value_id)

            node_info.mount(key_label)
            node_info.mount(value_label)

        node_status = self.query_one("#node-status")
        for key, value in details.render_status().items():
            value_id = f"node-status-value-{key}"
            if labels := node_status.query(f"Label#{value_id}"):
                value_label = labels[0]
                value_label.update(render(key, value))
                continue

            key_label = Label(f"[b]{key}[/b]")
            value_label = Label(render(key, value), id=value_id)

            node_status.mount(key_label)
            node_status.mount(value_label)

        resources = self.query_one("#resources")
        units = {"memory": "M"}
        exclude = {"billing", "nodes"}
        for key, (total, used) in details.resources().items():
            if key in exclude:
                continue

            value_id = f"resource-{key.replace('/', '_').replace(':', '_')}"
            if widgets := resources.query(f"ResourceBar#{value_id}"):
                widget = widgets[0]
                widget.used = as_unit(used, units.get(key))
                continue

            key_label = Label(f"[b]{key}[/b]")
            value_bar = render_resource(total, used, units.get(key))
            value_bar.id = value_id

            resources.mount(key_label)
            resources.mount(value_bar)

        self.push_data(
            details.time, details.cpu_load, details.real_memory - details.free_mem
        )
        time = [t.strftime(date_format) for t in self.time]

        right = self.time[-1]
        left = right - self.max_data_points * dt.timedelta(
            seconds=self.app.config.ping_interval
        )

        cpu = self.query_one("PlotextPlot#live-cpu")
        cpu.plt.clear_data()
        cpu.plt.date_form(date_pattern)
        cpu.plt.plot(time, self.cpu_load, color="blue", marker="braille")
        cpu.plt.xlim(left.strftime(date_format), right.strftime(date_format))
        cpu.plt.ylim(lower=0.0)
        cpu.refresh()

        mem = self.query_one("PlotextPlot#live-mem")
        mem.plt.clear_data()
        mem.plt.date_form(date_pattern)
        mem.plt.plot(time, self.used_memory, color="orange", marker="braille")
        mem.plt.xlim(left.strftime(date_format), right.strftime(date_format))
        mem.plt.ylim(lower=0.0)
        mem.refresh()
