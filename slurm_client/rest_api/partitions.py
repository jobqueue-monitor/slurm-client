from dataclasses import dataclass
from typing import Any

from textual.message import Message

from slurm_client.rest_api.request import request


@dataclass
class PartitionListMessage(Message):
    partitions: list[dict[str, Any]]


@request.get("/slurm/{version}/partitions")
def all_partitions(result: dict[str, Any]) -> PartitionListMessage:
    partitions = result.get("partitions", [])
    return PartitionListMessage(partitions)
