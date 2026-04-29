from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RadioButton, RadioSet


class SortScreen(ModalScreen):
    CSS_PATH = "sort.tcss"

    def __init__(self, columns):
        super().__init__()

        self.columns = columns

    def compose(self) -> ComposeResult:
        with Vertical(id="container"):
            with RadioSet(id="columns"):
                for column in self.columns:
                    yield RadioButton(column)

            with Horizontal():
                yield Button("Submit", id="submit")
                yield Button("Cancel", id="cancel", variant="error")

    @on(Button.Pressed, "#submit")
    def handle_sort(self) -> None:
        radio_set = self.query_one("RadioSet#columns")
        pressed = radio_set.pressed_button
        label = str(pressed.label) if pressed is not None else None

        self.dismiss(label)

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        self.dismiss(None)
