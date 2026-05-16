import re
from typing import TypedDict

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


def parse_resource_spec(spec: str) -> ResourceDict:
    decoded = {
        match.group("key"): match.group("value") for match in resource_re.finditer(spec)
    }
    translated = {translations.get(key, key): value for key, value in decoded.items()}

    return default_resources | translated


def parse_resources(total: str, used: str) -> ResourcesDict:
    return {"total": parse_resource_spec(total), "used": parse_resource_spec(used)}
