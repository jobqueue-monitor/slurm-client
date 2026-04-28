from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Footer, Label

from slurm_client.rest_api.ping import PingMessage


class SlurmClientFooter(Widget):
    """A customized footer for the slurm client."""

    DEFAULT_CSS = """
    SlurmClientFooter {
        dock: bottom;
        height: 1;
        background: $panel;
    }

    SlurmClientFooter #footer-inner {
        width: 60%;
    }

    SlurmClientFooter #footer-area > Label {
        margin-left: 2;
        margin-right: 2;
        width: auto;
        text-align: right;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="footer-area"):
            with Horizontal(id="footer-inner"):
                yield Footer()
            yield Label(id="server-info")

    @on(PingMessage)
    def refresh_server_status(self, msg: PingMessage) -> None:
        label = self.query_one("Label#server-info")
        label.update(msg.as_renderable())
