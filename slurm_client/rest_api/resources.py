import re
from typing import Any, NotRequired, TypedDict

value_re = re.compile(r"(?P<value>[0-9]+)(?P<units>[a-zA-Z]+)?")
resource_re = re.compile(r"(?P<key>[-a-z0-9_:/]+)=(?P<value>[0-9M]+)")
generic_resource_re = re.compile(
    r"""
    (?P<type>[a-z]+)
    :(?P<name>[^:]+)
    :(?P<quantity>[0-9]+)
    (?:
      \(
      (?P<modifier_code>[A-Z]+)
      :(?P<modifier_value>[-0-9]+|N/A)
      \)
    )?
    """,
    re.X,
)


class ResourceDict(TypedDict):
    cpu: str
    memory: str
    node: str


class GenericResourceDict(TypedDict):
    # no required members
    pass


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


class GenericResourcesDict(TypedDict):
    total: GenericResourceDict
    used: GenericResourceDict

    drained: NotRequired[GenericResourceDict]


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


def noop(x: Any) -> Any:
    return x


def extract_resource_group(match) -> dict[str, Any]:
    translations = {"S": "socket_affinity", "IDX": "index"}
    converters = {"quantity": int}

    modifier_code = match.group("modifier_code")
    if modifier_code is not None:
        modifier_value = match.group("modifier_value")
        if modifier_value == "N/A":
            value = []
        elif "-" in modifier_value:
            start, stop = map(int, modifier_value.split("-"))
            value = list(range(start, stop + 1))
        else:
            value = [int(modifier_value)]
        modifier = {translations[modifier_code]: value}
    else:
        modifier = {}

    resource = {
        name: converters.get(name, noop)(match.group(name))
        for name in ["type", "name", "quantity"]
    }

    return resource | modifier


def parse_generic_resource_spec(spec: str) -> list[GenericResourceDict]:
    return [
        extract_resource_group(match) for match in generic_resource_re.finditer(spec)
    ]
