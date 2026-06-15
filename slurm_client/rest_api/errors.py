from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slurm_client.types import JSON


@dataclass
class RestApiError(Exception):
    errno: int

    short_description: str
    long_description: str

    source: str

    def __repr__(self):
        return f"Error {self.errno} from {self.source}: {self.short_description}\n\n{self.long_description}"


def format_errors(errors: list[dict[str, JSON]]) -> RestApiError | ExceptionGroup:
    if len(errors) == 1:
        return format_error(errors[0])
    return ExceptionGroup("rest api request failed.", [format_error(e) for e in errors])


def format_error(e: dict[str, JSON]) -> RestApiError:
    return RestApiError(
        errno=e["error_number"],
        source=e["source"],
        short_description=e["error"],
        long_description=e["description"],
    )
