import itertools
import re
from typing import Any, TypedDict

from slurm_client.rest_api.request import request
from slurm_client.rest_api.table_message import TableContentFetched

node_group_re = re.compile(r"[-a-z0-9]+(?:\[[0-9]+(?:,[0-9]+)*\])?")
node_glob_re = re.compile(r"(?P<prefix>[-a-z0-9]+)(?:\[(?P<variations>[0-9,]+)\])?")


def _expand_glob(glob: str) -> list[str]:
    match = node_glob_re.fullmatch(glob)

    prefix = match.group("prefix")
    variations = match.group("variations")
    if variations is None:
        return [prefix]

    return [f"{prefix}{value}" for value in variations.split(",")]


def parse_node_list(nodes: dict[str, Any]) -> list[str]:
    if nodes["total"] == 0:
        return []

    configured = nodes["configured"]

    globs = node_group_re.findall(configured)
    return list(itertools.chain.from_iterable(_expand_glob(glob) for glob in globs))


class NodeSummary(TypedDict):
    name: str
    address: str
    hostname: str
    state: str
    partitions: list[str]


@request.get("/slurm/{version}/nodes")
def nodes_summary(result: dict[str, Any]) -> list[NodeSummary]:
    nodes = result.get("nodes", [])

    rows = [
        {
            "name": node["name"],
            "address": node["address"],
            "hostname": node["hostname"],
            "state": node["state"],
            "partitions": ", ".join(node["partitions"]),
        }
        for node in nodes
    ]

    return TableContentFetched("nodes", rows)
