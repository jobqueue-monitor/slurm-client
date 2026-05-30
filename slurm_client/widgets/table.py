from dataclasses import dataclass
from functools import cached_property

from textual import on
from textual.app import ComposeResult
from textual.events import Click
from textual.widget import Widget
from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist


@dataclass
class Sorting:
    name: str
    reverse: bool


class SortableTable(Widget):
    DEFAULT_CSS = """
    SortableTable {
        height: auto;
        width: auto;
    }
    """

    def __init__(self, columns: list[str], **kwargs) -> None:
        super().__init__(**kwargs)

        self.columns = columns
        self.sorting = Sorting(columns[0], reverse=False)

    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one("DataTable")
        for col in self.columns:
            table.add_column(col, key=col)

    @cached_property
    def data_table(self) -> DataTable:
        return self.query_one("DataTable")

    def focus(self) -> None:
        self.data_table.focus()

    @property
    def cursor_type(self) -> str:
        return self.data_table.cursor_type

    @cursor_type.setter
    def cursor_type(self, new_value: str) -> None:
        self.data_table.cursor_type = new_value

    @property
    def zebra_stripes(self) -> bool:
        return self.data_table.zebra_stripes

    @zebra_stripes.setter
    def zebra_stripes(self, new_value: bool) -> None:
        self.data_table.zebra_stripes = new_value

    def replace_contents(self, new_rows) -> None:
        table = self.data_table

        for row in new_rows:
            row_name = row[0]
            try:
                table.get_row(row_name)
            except RowDoesNotExist:
                table.add_row(*row, key=row_name)
            else:
                for col_name, value in zip(self.columns, row):
                    table.update_cell(row_name, col_name, value, update_width=True)

    @on(Click)
    async def on_click(self, event: Click) -> None:
        widget = event.widget
        if not isinstance(widget, DataTable):
            return

        hover_column = self.columns[widget.hover_column]

        current_sorting = self.sorting
        reverse = (
            not current_sorting.reverse
            if current_sorting.name == hover_column
            else False
        )

        widget.sort(hover_column, reverse=reverse)
        self.sorting = Sorting(name=hover_column, reverse=reverse)
