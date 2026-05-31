import datetime as dt
import itertools
import re
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Self, TypedDict

from slurm_client.rest_api.parsers import parse_datetime, parse_value_set
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import (
    GenericResourcesDict,
    ResourcesDict,
    parse_generic_resource_spec,
    parse_resource_spec,
)
from slurm_client.utils import identity

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


@dataclass
class NodeChangeReason:
    reason: str
    changed_at: dt.datetime
    set_by_user: str

    @classmethod
    def create(cls, reason, changed_at, set_by_user) -> Self | None:
        if reason == "" and set_by_user == "":
            return None

        return cls(reason, changed_at, set_by_user)


key_translations = {}
value_converters = {
    "free_mem": parse_value_set,
    "boot_time": parse_datetime,
    "last_busy": parse_datetime,
    "reason_changed_at": parse_datetime,
    "gres": parse_generic_resource_spec,
    "gres_used": parse_generic_resource_spec,
    "gres_drained": parse_generic_resource_spec,
    "tres": parse_resource_spec,
    "tres_used": parse_resource_spec,
}
drop = {
    "version",
    "topology",
    "temporary_disk",
    "slurmd_start_time",
    "reservation",
    "resume_after",
    "res_cores_per_gpu",
    "port",
    "next_state_after_reboot",
    "owner",
    "instance_id",
    "instance_type",
    "mcs_label",
    "burstbuffer_network_address",
    "cert_flags",
    "cluster_name",
    "energy",
    "external_sensors",
    "extra",
    "power",
    "tls_cert_last_renewal",
    "weight",
    "tres_weighted",
    "gpu_spec",
}
combined_keys = {
    "reason": (
        ["reason", "reason_changed_at", "reason_set_by_user"],
        NodeChangeReason.create,
    ),
    "trackable_resources": (
        ["tres", "tres_used"],
        lambda total, used: {"total": total, "used": used},
    ),
    "generic_resources": (
        ["gres", "gres_used", "gres_drained"],
        lambda total, used, drained: {"total": total, "used": used, "drained": drained},
    ),
}


class NodeSummary(TypedDict):
    name: str
    address: str
    hostname: str
    state: list[str]
    partitions: list[str]


class NodeInfo(TypedDict):
    address: str

    architecture: str
    boards: int
    sockets: int

    operating_system: str
    partitions: list[str]

    comment: str


class NodeStatus(TypedDict):
    state: list[str]

    boot_time: dt.datetime
    last_busy: dt.datetime | None


@dataclass
class NodeDetails:
    summary_columns: ClassVar[list[str]] = [
        "name",
        "address",
        "hostname",
        "state",
        "partitions",
    ]
    info_columns: ClassVar[list[str]] = [
        "address",
        "architecture",
        "boards",
        "sockets",
        "operating_system",
        "partitions",
        "comment",
    ]
    status_columns: ClassVar[list[str]] = [
        "state",
        "reason",
        "boot_time",
        "last_busy",
    ]

    time: dt.datetime

    # node info
    name: str
    address: str
    hostname: str

    features: list[str]
    active_features: list[str]

    state: list[str]
    reason: NodeChangeReason | None
    comment: str

    boot_time: dt.datetime
    last_busy: dt.datetime | None

    operating_system: str

    architecture: str
    boards: int
    cores: int
    sockets: int

    partitions: list[str]

    # resources
    # -- individual resources
    cpu_binding: int
    cpu_load: int

    cpus: int
    effective_cpus: int
    threads: int

    real_memory: int
    free_mem: int | None

    # -- system reservations
    specialized_cores: int
    specialized_cpus: str
    specialized_memory: int

    # -- allocated status
    alloc_cpus: int
    alloc_memory: int
    alloc_idle_cpus: int

    # -- combined resources
    trackable_resources: ResourcesDict
    generic_resources: GenericResourcesDict

    def render_summary(self) -> NodeSummary:
        mapping = asdict(self)
        return {k: mapping[k] for k in self.summary_columns}

    def render_info(self) -> NodeInfo:
        mapping = asdict(self)
        return {k: mapping[k] for k in self.info_columns}

    def render_status(self) -> NodeStatus:
        mapping = asdict(self)
        return {k: mapping[k] for k in self.status_columns}

    def resources(self) -> ResourcesDict:
        total = self.trackable_resources["total"]
        used = self.trackable_resources["used"]
        return {
            name: (total[name], used.get(name, 0))
            for name in self.trackable_resources["total"]
        }


def parse_node_details(time: dt.datetime, details: dict[str, Any]) -> NodeDetails:
    translated = {
        key_translations.get(key, key): value_converters.get(key, identity)(value)
        for key, value in details.items()
        if key not in drop
    }

    for new_name, (names, converter) in combined_keys.items():
        values = [translated[name] for name in names]
        for name in names:
            del translated[name]
        translated[new_name] = converter(*values)

    return NodeDetails(time=time, **translated)


@request.get("/slurm/{version}/nodes")
def all_nodes(result: dict[str, Any]) -> list[NodeDetails]:
    nodes = result.get("nodes", [])
    time = parse_datetime(result["last_update"])

    return [parse_node_details(time, node) for node in nodes]


@request.get("/slurm/{version}/node/{node_name}")
def node_details(result: dict[str, Any]) -> NodeDetails:
    node = result["nodes"][0]
    time = parse_datetime(result["last_update"])

    return parse_node_details(time, node)
