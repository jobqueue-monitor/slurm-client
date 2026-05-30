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
class Job:
    summary_columns: ClassVar[list[str]] = [
        "name",
        "user",
        "group",
        "partition",
        "start_time",
        "state",
    ]

    name: str
    user: str
    group: str
    partition: str
    start_time: dt.datetime
    state: list[str]

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
