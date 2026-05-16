import re
from typing import TypedDict

value_re = re.compile(r"(?P<value>[0-9]+)(?P<units>[a-zA-Z]+)?")
resource_re = re.compile(r"(?P<key>[-a-z0-9_:/]+)=(?P<value>[0-9M]+)")


class ResourceDict(TypedDict):
    cpu: str
    memory: str
    node: str


default_resources: ResourceDict = {
    "cpu": "0",
    "memory": "0M",
    "node": "0",
    "billing": "0",
}
translations = {"mem": "memory"}


class ResourcesDict(TypedDict):
    total: ResourceDict
    used: ResourceDict


def split_value(value: str | None) -> (int, str | None):
    if value is None:
        return 0, None

    match = value_re.fullmatch(value)
    if match is None:
        raise ValueError(f"cannot parse value: {value}")

    numeric_value = int(match.group("value"))
    units = match.group("units")

    return numeric_value, units


def parse_resource_spec(spec: str) -> ResourceDict:
    decoded = {
        match.group("key"): match.group("value") for match in resource_re.finditer(spec)
    }
    translated = {translations.get(key, key): value for key, value in decoded.items()}

    return translated


def parse_resources(total: str, used: str) -> ResourcesDict:
    return {
        "total": default_resources | parse_resource_spec(total),
        "used": default_resources | parse_resource_spec(used),
    }
