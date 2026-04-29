from dataclasses import dataclass
from typing import Any, TypedDict

from textual.message import Message

from slurm_client.rest_api.request import request
from slurm_client.rest_api.table_message import TableContentFetched


@dataclass
class PartitionListMessage(Message):
    partitions: list[dict[str, Any]]


class PartitionSummary(TypedDict):
    name: str
    total_nodes: int
    total_cpus: int
    state: str


@request.get("/slurm/{version}/partitions")
def all_partitions(result: dict[str, Any]) -> PartitionListMessage:
    partitions = result.get("partitions", [])
    return PartitionListMessage(partitions)


@request.get("/slurm/{version}/partitions")
def partitions_summary(result: dict[str, Any]) -> TableContentFetched:
    partitions = result.get("partitions", [])

    rows = [
        {
            "name": partition["name"],
            "total_nodes": partition["nodes"]["total"],
            "total_cpus": partition["cpus"]["total"],
            "state": partition["partition"]["state"][0],
        }
        for partition in partitions
    ]

    return TableContentFetched("partitions", rows)
