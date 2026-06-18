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
        processed = {str(r[0]): r for r in new_rows}

        for row_key, row in processed.items():
            try:
                existing_row = self.get_row(row_key)
            except RowDoesNotExist:
                self.add_row(*row, key=row_key)
            else:
                for col_key, value, existing_value in zip(
                    self.columns, row, existing_row
                ):
                    if value == existing_value:
                        continue
                    self.update_cell(row_key, col_key, value, update_width=True)

        existing_rows = {k.value for k in self.rows.keys()}
        for to_delete in existing_rows - processed.keys():
            self.remove_row(to_delete)

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
