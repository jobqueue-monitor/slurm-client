from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar, TypedDict

from textual.message import Message

from slurm_client.rest_api.nodes import NodeDetails, parse_node_list
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import (
    ResourceDict,
    ResourcesDict,
    default_resources,
    parse_resource_spec,
    parse_resources,
)


@dataclass
class PartitionListMessage(Message):
    partitions: list[dict[str, Any]]


class PartitionSummary(TypedDict):
    name: str

    total_nodes: int
    total_cpus: int

    states: list[str]


@dataclass
class Partition:
    summary_columns: ClassVar[list[str]] = [
        "name",
        "total_nodes",
        "total_cpus",
        "states",
    ]

    name: str
    alternate: str

    states: list[str]

    cpus: int
    nodes: list[str]
    tracked_resources: ResourceDict

    def render_summary(self) -> PartitionSummary:
        return {
            "name": self.name,
            "total_nodes": len(self.nodes),
            "total_cpus": self.cpus,
            "states": self.states,
        }


@dataclass
class PartitionDetails(Message):
    name: str
    alternate: str

    states: list[str]

    nodes: list[str] | list[NodeDetails]
    tracked_resources: ResourcesDict


def parse_partition(partition: dict[str, Any]) -> Partition:
    return Partition(
        name=partition["name"],
        alternate=partition["alternate"],
        states=partition["partition"]["state"],
        cpus=partition["cpus"]["total"],
        nodes=parse_node_list(partition["nodes"]),
        tracked_resources=parse_resources(partition["tres"]["configured"], ""),
    )


@request.get("/slurm/{version}/partitions")
def all_partitions(result: dict[str, Any]) -> list[Partition]:
    partitions = result.get("partitions", [])
    return [parse_partition(partition) for partition in partitions]


@request.get("/slurm/{version}/partitions")
def partitions_summary(result: dict[str, Any]) -> list[PartitionSummary]:
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

    return rows


@request.get("/slurm/{version}/partition/{partition_name}")
def partition_details(result: dict[str, Any]) -> PartitionDetails:
    partition = result["partitions"][0]

    name = partition["name"]
    alternate = partition["alternate"]
    nodes = parse_node_list(partition["nodes"])
    states = partition["partition"]["state"]

    tres = parse_resources(
        partition["tres"]["configured"],
        "",
    )

    return PartitionDetails(
        name=name,
        alternate=alternate,
        states=states,
        nodes=nodes,
        tracked_resources=tres,
    )


@request.get("/slurm/{version}/nodes")
def resource_usage(result: dict[str, Any], partition: str) -> ResourceDict:
    nodes = [
        node
        for node in result["nodes"]
        if (
            partition in node.get("partitions", [])
            and set(node["state"]).intersection({"IDLE", "MIXED"})
        )
    ]

    used_tres = [
        default_resources | parse_resource_spec(node["tres_used"]) for node in nodes
    ]
    column_wise_tres = defaultdict(lambda: 0)
    for tres in used_tres:
        for name, value in tres.items():
            column_wise_tres[name] += value

    used_gres = [parse_resource_spec(node["gres_used"]) for node in nodes]
    column_wise_gres = defaultdict(lambda: 0)
    for tres in used_gres:
        for name, value in tres.items():
            column_wise_gres[name] += value

    return dict(column_wise_tres | column_wise_gres)
