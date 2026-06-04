import datetime as dt
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, TypedDict

from slurm_client.rest_api.parsers import parse_datetime
from slurm_client.rest_api.request import request


class JobSummary(TypedDict):
    name: str
    user: str
    group: str
    partition: str
    start_time: dt.datetime
    state: list[str]


@dataclass
class Signal:
    id: int
    name: str


@dataclass
class ExitCode:
    status: list[str]
    return_code: int
    signal: Signal


@dataclass
class JobResources:
    pass


@dataclass
class Job:
    summary_columns: ClassVar[list[str]] = [
        "name",
        "user",
        "group",
        "partition",
        "start_time",
        "state",
    ]

    time: dt.datetime

    name: str
    user: str
    group: str

    user_id: int
    group_id: int

    allocating_node: str
    batch_host: str
    batch_features: str
    partition: str

    flags: list[str]

    command: str

    container: str | None
    container_id: str | None
    container_type: str | None

    contiguous: bool

    core_spec: int
    thread_spec: int
    cores_per_socket: int

    cron: str
    deadline: str
    dependency: str

    derived_exit_code: ExitCode

    start_time: dt.datetime
    eligible_time: dt.datetime
    end_time: dt.datetime

    excluded_nodes: list[str]
    exit_code: ExitCode
    failed_node: str

    extra: str
    features: list[str]

    gres_detail: list[str]
    job_id: int
    job_resources: JobResources

    mail_type: list[str]
    mail_user: str

    max_cpus: int
    max_nodes: int

    memory_per_tres: str
    memory_update_delay: int
    memory_update_margin: int

    netowrk: str
    nodes: str
    nice: int

    cpus: int
    node_count: int

    memory_per_cpu: int
    memory_per_node: int

    minimum_cpus_per_node: int
    minimum_tmp_disk_per_node: int

    preempt_time: dt.datetime
    preemtable_time: dt.datetime

    pre_sus_time: dt.datetime

    hold: bool

    reboot: bool
    requeue: bool
    required_nodes: list[str]

    resize_time: dt.datetime
    restart_count: int
    scheduled_nodes: list[str]
    selinux_context: str

    sockets_per_board: int
    sockets_per_node: int

    standard_input: str
    standard_output: str
    standard_error: str

    stdin_expanded: str
    stdout_expanded: str
    stderr_expanded: str

    submit_line: str
    suspend_time: dt.datetime

    system_comment: str
    state: list[str]

    time_limit: int
    time_minimum: int

    threads_per_core: int

    tres_bind: str
    tres_freq: str
    tres_per_job: str
    tres_per_node: str
    tres_per_socket: str
    tres_per_task: str
    tres_req_str: str
    tres_alloc_str: str

    current_working_directory: str

    def render_summary(self) -> JobSummary:
        return {k: v for k, v in asdict(self).items() if k in self.summary_columns}


@request.get("/slurm/{version}/jobs")
def all_jobs(result: dict[str, Any]) -> list[Job]:
    jobs = result.get("jobs", [])

    rows = [
        Job(
            name=job["name"],
            user=job["user_name"],
            group=job["group_name"],
            partition=job["partition"],
            start_time=parse_datetime(job["start_time"]),
            state=job["job_state"],
        )
        for job in jobs
    ]

    return rows
