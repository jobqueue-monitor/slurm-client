import datetime as dt
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from slurm_client.rest_api.errors import format_errors
from slurm_client.rest_api.nodes import parse_node_list
from slurm_client.rest_api.parsers import parse_datetime, parse_value_set
from slurm_client.rest_api.request import request
from slurm_client.rest_api.resources import ResourceDict, parse_resource_spec
from slurm_client.utils import identity

if TYPE_CHECKING:
    from typing import Any, Self

    from slurm_client.types import JSON


def replace_time(time: dt.datetime) -> dt.datetime | None:
    if time.timestamp() == 0:
        return None

    return time


@dataclass
class JobSummary:
    id: int
    name: str
    user: str
    group: str
    partition: str
    time: dt.datetime
    state: list[str]
    reason: str

    def render_summary(self):
        return asdict(self)


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

    account: str
    qos: str

    partition: str

    submit_line: str
    submit_time: dt.datetime

    mail_type: list[str]
    mail_user: str

    allocating_node: str

    def render(self) -> dict[str, Any]:
        return {
            "user": f"{self.user} ({self.user_id})",
            "group": f"{self.group} ({self.group_id})",
            "account": self.account,
            "qos": self.qos,
            "partition": self.partition,
            "submission command": self.submit_line,
            "submitted at": self.submit_time,
            "allocating node": self.allocating_node,
            "mail settings": f"{', '.join(self.mail_type) or 'none'}, mails to {self.mail_user}",
        }


@dataclass
class JobDetails:
    id: int
    name: str
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

    def render(self):
        exclude = {
            "selinux_context",
            "batch_job",
            "batch_features",
            "array_job_id",
            "array_task_id",
            "array_max_tasks",
            "array_task",
            "container",
            "container_id",
            "container_type",
        }
        names = {
            "current_working_directory": "working directory",
            "restart_count": "number of restarts",
            "system_comment": "comment",
        }
        return {
            names.get(key, key): value
            for key, value in asdict(self).items()
            if key not in exclude
        }


@dataclass
class JobResource:
    allocated: int
    used: int

    @classmethod
    def from_dict(cls, mapping: dict[str, int]) -> Self:
        match mapping:
            case {"count": allocated, "used": used}:
                return cls(allocated=allocated, used=used)
            case {"allocated": allocated, "used": used}:
                return cls(allocated=allocated, used=mapping["used"])

        raise ValueError(f"invalid job resources: {mapping}")


@dataclass
class JobResourceCore:
    index: int
    status: list[str]


@dataclass
class JobSocket:
    index: int
    cores: list[JobResourceCore]

    @classmethod
    def from_dict(cls, mapping: dict[str, JSON]) -> Self:
        return cls(
            index=mapping["index"],
            cores=[JobResourceCore(**core) for core in mapping["cores"]],
        )


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


def _parse_allocation(data: dict[str, JSON]) -> JobNode:
    return JobNode(
        index=data["index"],
        name=data["name"],
        cpus=JobResource.from_dict(data["cpus"]),
        memory=JobResource.from_dict(data["memory"]),
        sockets=[JobSocket.from_dict(socket) for socket in data["sockets"]],
    )


def _parse_nodes(data: dict[str, JSON]) -> JobNodes:
    return JobNodes(
        select_type=data["select_type"],
        allocated_nodes=parse_node_list(data["list"]),
        whole=data["whole"],
        allocation=[_parse_allocation(alloc) for alloc in data["allocation"]],
    )


@dataclass
class JobResourceDetails:
    select_type: list[str]
    cpus: int
    threads_per_core: int | None

    nodes: JobNodes


def _parse_resource_details(data: dict[str, JSON] | None) -> JobResourceDetails | None:
    if data is None:
        return None

    return JobResourceDetails(
        select_type=data["select_type"],
        cpus=data["cpus"],
        threads_per_core=parse_value_set(data["threads_per_core"]),
        nodes=_parse_nodes(data["nodes"]),
    )


@dataclass
class JobResources:
    time_minimum: int
    min_cpus: int
    max_cpus: int
    max_nodes: int

    time_limit: int

    node_count: int
    allocated_nodes: list[str]
    network: str

    memory_per_tres: str

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
    resource_details: JobResourceDetails
    tres_per_job: ResourceDict
    tres_per_node: ResourceDict
    tres_per_task: ResourceDict

    tres_requested: ResourceDict
    tres_allocated: ResourceDict


@dataclass
class JobStatus:
    state: list[str]
    reason: str
    description: str

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

    def render(self):
        translations = {
            "start_time": "started at",
            "suspend_time": "suspended at",
            "eligible_time": "eligible at",
            "resize_time": "resized at",
            "end_time": "terminated at",
            "stdin_expanded": "standard input",
            "stdout_expanded": "standard output",
            "stderr_expanded": "standard error",
        }
        transformations = {
            "start_time": replace_time,
            "suspend_time": replace_time,
            "resize_time": replace_time,
            "eligible_time": replace_time,
            "end_time": replace_time,
        }
        all = {
            key: (translations.get(key, key), transformations.get(key, identity)(value))
            for key, value in asdict(self).items()
        }
        all["state"] = (
            "state",
            f"{', '.join(self.state)} ({self.reason}): {self.description}",
        )
        status_keys = ["state", "hold", "exit_code", "derived_exit_code", "failed_node"]
        times_keys = [
            "start_time",
            "suspend_time",
            "resize_time",
            "eligible_time",
            "end_time",
        ]
        logs_keys = ["stdin_expanded", "stdout_expanded", "stderr_expanded"]

        return {
            "status": dict(all[k] for k in status_keys),
            "times": dict(all[k] for k in times_keys),
            "logs": dict(all[k] for k in logs_keys),
        }


@dataclass
class JobScheduling:
    cron: str
    contiguous: bool
    deadline: str
    excluded_nodes: list[str]
    required_nodes: list[str]
    scheduled_nodes: list[str]  # resources?
    requeue: bool

    def render(self):
        return {
            "cron": self.cron,
            "contiguous nodes requested": self.contiguous,
            "schedule before": self.deadline,
            "requeue requested": self.requeue,
        }


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
            case "COMPLETED" | "TIMEOUT":
                time = self.status.end_time
            case _:
                time = self.status.start_time

        return JobSummary(
            id=self.info.id,
            name=self.info.name,
            user=self.submission.user,
            group=self.submission.group,
            partition=self.info.partition,
            time=time,
            state=state,
            reason=self.status.reason,
        )


def _extract_submission(data: dict[str, JSON]) -> JobSubmission:
    return JobSubmission(
        user=data["user_name"],
        group=data["group_name"],
        user_id=data["user_id"],
        group_id=data["group_id"],
        account=data["account"],
        qos=data["qos"],
        partition=data["partition"],
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
        reason=data["state_reason"] if data["state_reason"] != "None" else None,
        description=data["state_description"],
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
    return JobResources(
        allocated_nodes=parse_node_list(data["nodes"]),
        network=data["network"],
        resource_details=_parse_resource_details(data["job_resources"]),
        max_cpus=parse_value_set(data["max_cpus"]),
        max_nodes=parse_value_set(data["max_nodes"]),
        memory_per_tres=data["memory_per_tres"],
        min_cpus=parse_value_set(data["cpus"]),
        node_count=parse_value_set(data["node_count"]),
        reboot=data["reboot"],
        memory_per_cpu=parse_value_set(data["memory_per_cpu"]),
        memory_per_node=parse_value_set(data["memory_per_node"]),
        threads_per_core=parse_value_set(data["threads_per_core"]),
        sockets_per_board=data["sockets_per_board"],
        sockets_per_node=parse_value_set(data["sockets_per_node"]),
        minimum_cpus_per_node=parse_value_set(data["minimum_cpus_per_node"]),
        minimum_tmp_disk_per_node=parse_value_set(data["minimum_tmp_disk_per_node"]),
        core_spec=data["core_spec"],
        thread_spec=data["thread_spec"],
        cores_per_socket=parse_value_set(data["cores_per_socket"]),
        gres_detail=data["gres_detail"],
        time_limit=parse_value_set(data["time_limit"]),
        time_minimum=parse_value_set(data["time_minimum"]),
        tres_per_job=parse_resource_spec(data["tres_per_job"]),
        tres_per_node=parse_resource_spec(data["tres_per_node"]),
        tres_per_task=parse_resource_spec(data["tres_per_task"]),
        tres_requested=parse_resource_spec(data["tres_req_str"]),
        tres_allocated=parse_resource_spec(data["tres_alloc_str"]),
    )


def _extract_scheduling(data: dict[str, JSON]) -> JobScheduling:
    return JobScheduling(
        cron=data["cron"],
        contiguous=data["contiguous"],
        deadline=parse_datetime(data["deadline"]),
        excluded_nodes=data["excluded_nodes"],
        required_nodes=data["required_nodes"],
        scheduled_nodes=data["scheduled_nodes"],
        requeue=data["requeue"],
    )


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


def _parse_job_summary(data: dict[str, JSON]) -> JobSummary:
    state = data["job_state"][0]
    reason = (
        data["state_reason"] if data.get("state_reason") not in ("None", "") else None
    )
    match state:
        case "RUNNING":
            time = parse_datetime(data["start_time"])
        case "PENDING":
            time = parse_datetime(data["submit_time"])
        case "COMPLETED" | "TIMEOUT":
            time = parse_datetime(data["end_time"])
        case _:
            time = parse_datetime(data["start_time"])

    return JobSummary(
        id=data["job_id"],
        name=data["name"],
        user=data["user_name"],
        group=data["group_name"],
        partition=data["partition"],
        time=time,
        state=state,
        reason=reason,
    )


@request.get("/slurm/{version}/jobs")
def all_jobs(result: dict[str, JSON]) -> list[JobSummary]:
    jobs = result.get("jobs", [])
    rows = [_parse_job_summary(job) for job in jobs]

    return rows


@request.get("/slurm/{version}/job/{job_id}")
def job_details(result: dict[str, JSON]) -> Job:
    jobs = result.get("jobs")
    if jobs is None:
        raise format_errors(result["errors"])
    time = parse_datetime(result["last_update"])

    return _parse_job(time, jobs[0])
