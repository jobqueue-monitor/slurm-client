import math
from dataclasses import dataclass
from typing import Any

from textual.message import Message

from slurm_client.rest_api.request import request


@dataclass
class PingMessage(Message):
    server: str
    latency: float
    version: str

    def as_renderable(self) -> str:
        status = "🟢" if not math.isnan(self.latency) else "🔴"
        values = {
            "name": self.server,
            "latency": f"{self.latency:.3f} ms",
            "version": self.version,
        }
        sections = " | ".join(
            [f"[b]{name}[/b]: {value}" for name, value in values.items()]
        )
        return f"[b]slurm server[/b]: {status} {sections}"


@request.get("/slurm/{version}/ping")
def ping(result: dict[str, Any]) -> PingMessage:
    if "pings" not in result or len(result["pings"]) == 0:
        return {
            "server": "unknown",
            "latency": float("nan"),
            "version": "n/a",
        }

    p = result["pings"][0]
    slurm_version = result["meta"]["slurm"]["release"]

    return PingMessage(
        server=p["hostname"],
        latency=p["latency"] / 1000,
        version=slurm_version,
    )
