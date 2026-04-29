import datetime as dt
from typing import Any, TypedDict

from slurm_client.rest_api.request import request
from slurm_client.rest_api.table_message import TableContentFetched


class JobSummary(TypedDict):
    name: str
    user: str
    group: str
    partition: str
    start_time: str
    state: str


@request.get("/slurm/{version}/jobs")
def jobs_summary(result: dict[str, Any]) -> list[JobSummary]:
    jobs = result.get("jobs", [])

    rows = [
        {
            "name": job["name"],
            "user": job["user_name"],
            "group": job["group_name"],
            "partition": job["partition"],
            "start_time": dt.datetime.fromtimestamp(
                job["start_time"]["number"], tz=dt.UTC
            ),
            "state": job["job_state"][0],
        }
        for job in jobs
    ]

    return TableContentFetched("jobs", rows)
