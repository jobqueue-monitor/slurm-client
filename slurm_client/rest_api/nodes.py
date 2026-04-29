from typing import Any, TypedDict

from slurm_client.rest_api.request import request
from slurm_client.rest_api.table_message import TableContentFetched


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
