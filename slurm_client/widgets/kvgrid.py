from typing import Any

from textual.containers import Container
from textual.widgets import Label


class KeyValueGrid(Container):
    DEFAULT_CSS = """
    KeyValueGrid {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 12fr;
        height: auto;
    }
    """

    def upsert(self, name: str, value: Any, id: str) -> None:
        if labels := self.query(f"Label#{id}"):
            value_label = labels[0]
            value_label.update(value)
        else:
            key_label = Label(f"[b]{name}[/b]", classes="kvgrid-key")
            value_label = Label(value, id=id)

            self.mount(key_label)
            self.mount(value_label)

    def upsert_many(self, mapping: dict[str, Any], id_template: str) -> None:
        for k, v in mapping.items():
            self.upsert(k, v, id=id_template.format(key=k.replace(" ", "_")))
