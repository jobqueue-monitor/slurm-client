from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, RadioSet


class SortScreen(ModalScreen):
    CSS_PATH = "sort.tcss"

    def __init__(self, columns):
        super().__init__()

        self.columns = columns

    def compose(self) -> ComposeResult:
        yield Grid(
            RadioSet(*self.columns, id="columns"),
            Button("Submit", id="submit"),
            Button("Cancel", id="cancel", variant="error"),
            id="dialog",
        )

    @on(Button.Pressed, "#submit")
    def handle_sort(self) -> None:
        radio_set = self.query_one("RadioSet#columns")
        pressed = radio_set.pressed_button
        label = str(pressed.label) if pressed is not None else None

        self.dismiss(label)

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        self.dismiss(None)
