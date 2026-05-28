from dataclasses import dataclass
from typing import ClassVar

import httpx
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label


@dataclass
class NetworkError(Message):
    response: httpx.Response


@dataclass
class FatalError(Message):
    context: ClassVar[str]
    reason: str

    def render(self):
        return "\n".join([self.context, "", f"[i]{self.reason}[/i]"])


@dataclass
class SSHError(FatalError):
    context: ClassVar[str] = "Connecting to the ssh server failed:"
    reason: str


@dataclass
class TokenError(FatalError):
    context: ClassVar[str] = "Failed to create a token:"
    reason: str


class ParametrizedErrorScreen(ModalScreen):
    CSS_PATH = "error.tcss"

    def __init__(self, title: str, error: str, button_text: str = "Ok"):
        super().__init__()

        self.title = title
        self.error = error
        self.button_text = button_text

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with Container():
                yield Label(f"[b]{self.title}[/b]", id="title")
            yield Label(id="message")
            yield Button(self.button_text, variant="error", id="ack")

    def on_mount(self):
        msg = self.query_one("Label#message")
        msg.update(self.error)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ack":
            self.dismiss(True)


class FatalErrorScreen(ParametrizedErrorScreen):
    def __init__(self, error: str):
        super().__init__(title="Fatal Error", error=error, button_text="Quit")


class ErrorScreen(ParametrizedErrorScreen):
    def __init__(self, error: str):
        super().__init__(title="Error", error=error, button_text="Ok")
