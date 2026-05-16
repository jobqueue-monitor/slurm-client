from dataclasses import dataclass
from typing import Any, TypedDict

from textual.message import Message

from slurm_client.rest_api.nodes import parse_node_list
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import ResourcesDict, parse_resources
from slurm_client.rest_api.table_message import TableContentFetched


@dataclass
class PartitionListMessage(Message):
    partitions: list[dict[str, Any]]


@dataclass
class PartitionDetails(Message):
    name: str
    alternate: str

    states: list[str]

    nodes: list[str]
    tracked_resources: ResourcesDict


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


@request.get("/slurm/{version}/partition/{partition_name}")
def partition_details(result: dict[str, Any]) -> PartitionDetails:
    partition = result["partitions"][0]

    name = partition["name"]
    alternate = partition["alternate"]
    nodes = parse_node_list(partition["nodes"])
    states = partition["partition"]["state"]

    tres = parse_resources(
        partition["tres"]["configured"],
        partition.get("tres_used", {"configured": ""})["configured"],
    )

    return PartitionDetails(
        name=name,
        alternate=alternate,
        states=states,
        nodes=nodes,
        tracked_resources=tres,
    )
