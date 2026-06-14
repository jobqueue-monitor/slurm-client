import datetime as dt
from dataclasses import dataclass
from typing import Any, TypedDict

from slurm_client.rest_api.parsers import parse_datetime
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import ResourceDict


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
class JobSubmission:
    user: str
    user_id: int
    group: str
    group_id: int

    submit_line: str
    submit_time: dt.datetime

    mail_type: list[str]
    mail_user: str

    allocating_node: str


@dataclass
class JobDetails:
    id: int
    name: str
    partition: str
    command: str
    dependency: str
    nice: int

    current_working_directory: str
    container: str | None
    container_id: str | None
    container_type: str | None
    selinux_context: str

    restart_count: int
    features: list[str]  # remove?

    batch_job: bool
    batch_host: str
    batch_features: str  # remove?

    system_comment: str

    array_job_id: int | None
    array_task_id: int | None
    array_max_tasks: int | None
    array_task: str


@dataclass
class JobResource:
    allocated: int
    used: int


@dataclass
class JobResourceCore:
    index: int
    status: list[str]


@dataclass
class JobSocket:
    index: int
    cores: list[JobResourceCore]


@dataclass
class JobNode:
    index: int
    name: str

    cpus: JobResource
    memory: JobResource

    sockets: list[JobSocket]


@dataclass
class JobNodes:
    select_type: list[str]
    allocated_nodes: list[str]
    whole: bool

    allocation: list[JobNode]


@dataclass
class JobResourceDetails:
    select_type: list[str]
    cpus: int
    threads_per_core: int | None

    nodes: JobNodes


@dataclass
class JobResources:
    allocated_nodes: list[str]
    network: str

    resource_details: JobResourceDetails

    max_cpus: int
    max_nodes: int

    memory_per_tres: str
    memory_update_delay: int
    memory_update_margin: int

    cpus: int
    node_count: int
    reboot: bool

    memory_per_cpu: int
    memory_per_node: int

    threads_per_core: int
    sockets_per_board: int
    sockets_per_node: int

    minimum_cpus_per_node: int
    minimum_tmp_disk_per_node: int
    core_spec: int
    thread_spec: int
    cores_per_socket: int

    gres_detail: list[str]

    tres_bind: ResourceDict  # remove?
    tres_freq: ResourceDict  # remove?

    tres_per_job: ResourceDict
    tres_per_node: ResourceDict
    tres_per_socket: ResourceDict
    tres_per_task: ResourceDict

    tres_requested: ResourceDict
    tres_allocated: ResourceDict


@dataclass
class JobStatus:
    state: list[str]

    hold: bool
    flags: list[str]
    derived_exit_code: ExitCode
    exit_code: ExitCode
    failed_node: str

    start_time: dt.datetime
    suspend_time: dt.datetime
    resize_time: dt.datetime
    eligible_time: dt.datetime
    end_time: dt.datetime
    preempt_time: dt.datetime
    preemtable_time: dt.datetime
    pre_sus_time: dt.datetime

    standard_input: str
    standard_output: str
    standard_error: str

    stdin_expanded: str
    stdout_expanded: str
    stderr_expanded: str


@dataclass
class JobScheduling:
    cron: str
    contiguous: bool
    deadline: str
    excluded_nodes: list[str]
    required_nodes: list[str]
    scheduled_nodes: list[str]  # resources?
    time_limit: int
    time_minimum: int
    requeue: bool


@dataclass
class Job:
    time: dt.datetime

    submission: JobSubmission
    info: JobDetails
    resources: JobResources
    status: JobStatus
    scheduling: JobScheduling

    extra: str

    def render_summary(self) -> JobSummary:
        state = self.status.state[0]
        match state:
            case "RUNNING":
                time = self.status.start_time
            case "PENDING":
                time = self.submission.submit_time
            case _:
                time = self.status.start_time

        return {
            "name": self.info.name,
            "user": self.submission.user,
            "group": self.submission.group,
            "partition": self.info.partition,
            "time": time,
        }


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
