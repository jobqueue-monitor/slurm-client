from dataclasses import dataclass
from typing import Any

from textual.message import Message


@dataclass
class PartitionListMessage(Message):
    partitions: list[dict[str, Any]]


def process_partitions_result(result: dict[str, Any]) -> PartitionListMessage:
    partitions = result.get("partitions", [])
    return PartitionListMessage(partitions)
