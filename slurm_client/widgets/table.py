from dataclasses import dataclass

from textual import on
from textual.events import Click
from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist


@dataclass
class Sorting:
    name: str
    reverse: bool


class SortableTable(DataTable):
    def __init__(self, columns: list[str], **kwargs) -> None:
        super().__init__(**kwargs)

        self._column_names = columns
        for col in columns:
            self.add_column(col, key=col)
        self._sorting = Sorting(columns[0], reverse=False)

    def replace_contents(self, new_rows) -> None:
        for row in new_rows:
            row_name = row[0]
            try:
                self.get_row(row_name)
            except RowDoesNotExist:
                self.add_row(*row, key=row_name)
            else:
                for col_name, value in zip(self.columns, row):
                    self.update_cell(row_name, col_name, value, update_width=True)

    @on(Click)
    async def on_click(self, event: Click) -> None:
        widget = event.widget
        if not isinstance(widget, DataTable) or widget.hover_row != -1:
            return

        hover_column = self._column_names[widget.hover_column]

        current_sorting = self._sorting
        reverse = (
            not current_sorting.reverse
            if current_sorting.name == hover_column
            else False
        )

        widget.sort(hover_column, reverse=reverse)
        self._sorting = Sorting(name=hover_column, reverse=reverse)
