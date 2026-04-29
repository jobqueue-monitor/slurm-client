from dataclasses import dataclass
from typing import Any

from textual.message import Message


@dataclass
class TableContentFetched(Message):
    kind: str
    content: list[dict[str, Any]]

    def rows(self):
        for row in self.content:
            yield list(row.values())
