import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from slurm_client.rest_api.parsers import parse_datetime, parse_value_set
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import ResourceDict

if TYPE_CHECKING:
    from slurm_client.types import JSON


class JobSummary(TypedDict):
    name: str
    user: str
    group: str
    partition: str
    time: dt.datetime
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


def parse_exit_code(x: dict[str, JSON]) -> ExitCode:
    return ExitCode(
        status=x["status"],
        return_code=parse_value_set(x["return_code"]),
        signal=Signal(id=parse_value_set(x["signal"]["id"]), name=x["signal"]["name"]),
    )


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
            case "PENDING" | "TIMEOUT":
                time = self.submission.submit_time
            case "COMPLETED":
                time = self.submission.end_time
            case _:
                time = self.status.start_time

        return {
            "name": self.info.name,
            "user": self.submission.user,
            "group": self.submission.group,
            "partition": self.info.partition,
            "time": time,
            "state": state,
        }


def _extract_submission(data: dict[str, JSON]) -> JobSubmission:
    return JobSubmission(
        user=data["user_name"],
        group=data["group_name"],
        user_id=data["user_id"],
        group_id=data["group_id"],
        submit_line=data["submit_line"],
        submit_time=parse_datetime(data["submit_time"]),
        mail_type=data["mail_type"],
        mail_user=data["mail_user"],
        allocating_node=data["allocating_node"],
    )


def _extract_info(data: dict[str, JSON]) -> JobDetails:
    return JobDetails(
        id=data["job_id"],
        name=data["name"],
        partition=data["partition"],
        command=data["command"],
        dependency=data["dependency"],
        nice=data["nice"],
        current_working_directory=data["current_working_directory"],
        container=data["container"],
        container_id=data["container_id"],
        container_type=data.get("container_type"),
        selinux_context=data["selinux_context"],
        restart_count=data["restart_cnt"],
        features=data["features"],
        batch_job=data.get("batch_job"),
        batch_host=data["batch_host"],
        batch_features=data["batch_features"],
        system_comment=data["system_comment"],
        array_job_id=parse_value_set(data["array_job_id"]),
        array_task_id=parse_value_set(data["array_task_id"]),
        array_max_tasks=parse_value_set(data["array_max_tasks"]),
        array_task=data["array_task_string"],
    )


def _extract_status(data: dict[str, JSON]) -> JobStatus:
    return JobStatus(
        state=data["job_state"],
        hold=data["hold"],
        flags=data["flags"],
        derived_exit_code=parse_exit_code(data["derived_exit_code"]),
        exit_code=parse_exit_code(data["exit_code"]),
        failed_node=data["failed_node"],
        start_time=parse_datetime(data["start_time"]),
        suspend_time=parse_datetime(data["suspend_time"]),
        resize_time=parse_datetime(data["resize_time"]),
        eligible_time=parse_datetime(data["eligible_time"]),
        end_time=parse_datetime(data["end_time"]),
        preempt_time=parse_datetime(data["preempt_time"]),
        preemtable_time=parse_datetime(data.get("preemtable_time", {"set": False})),
        pre_sus_time=parse_datetime(data["pre_sus_time"]),
        standard_input=data["standard_input"],
        standard_output=data["standard_output"],
        standard_error=data["standard_error"],
        stdin_expanded=data["stdin_expanded"],
        stdout_expanded=data["stdout_expanded"],
        stderr_expanded=data["stderr_expanded"],
    )


def _extract_resources(data: dict[str, JSON]) -> JobResources:
    pass


def _extract_scheduling(data: dict[str, JSON]) -> JobScheduling:
    pass


def _parse_job(time: dt.datetime, data: dict[str, JSON]) -> Job:
    return Job(
        time=time,
        submission=_extract_submission(data),
        info=_extract_info(data),
        resources=_extract_resources(data),
        status=_extract_status(data),
        scheduling=_extract_scheduling(data),
        extra=data["extra"],
    )


@request.get("/slurm/{version}/jobs")
def all_jobs(result: dict[str, JSON]) -> list[Job]:
    jobs = result.get("jobs", [])
    time = parse_datetime(result["last_update"])

    rows = [_parse_job(time, job) for job in jobs]

    return rows
