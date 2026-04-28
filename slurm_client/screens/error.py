from dataclasses import dataclass

import httpx
from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label


@dataclass
class NetworkError(Message):
    response: httpx.Response


class ErrorScreen(ModalScreen):
    def __init__(self, error: str):
        super().__init__()
        self.error = error

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label("Error", id="title")
            yield Label(id="message")
            yield Button("Ok", variant="error", id="ack")

    def on_mount(self):
        msg = self.query_one("Label#message")
        msg.update(self.error)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ack":
            self.app.pop_screen()
