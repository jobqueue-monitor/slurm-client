import re
from typing import Any, TypedDict

from slurm_client.utils import identity

value_re = re.compile(r"(?P<value>[0-9]+)(?P<units>[a-zA-Z]+)?")
resource_re = re.compile(r"(?P<key>[-a-z0-9_:/]+)=(?P<value>[0-9A-Z]+)")
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
    "cpu": 0,
    "memory": 0,
    "node": 0,
    "billing": 0,
}
translations = {"mem": "memory"}


class ResourcesDict(TypedDict):
    total: ResourceDict
    used: ResourceDict


class GenericResourcesDict(TypedDict):
    total: GenericResourceDict
    used: GenericResourceDict

    drained: GenericResourceDict | None


def split_value(value: str | None) -> (int, str | None):
    if value in ("", None):
        return 0, None

    match = value_re.fullmatch(value)
    if match is None:
        raise ValueError(f"cannot parse value: {value}")

    numeric_value = int(match.group("value"))
    units = match.group("units")

    return numeric_value, units


factors = {"K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}


def decode_unit(value: str | None) -> int:
    numeric_value, unit = split_value(value)
    if unit is None:
        return numeric_value

    return numeric_value * factors[unit]


def as_unit(value: int, unit: str | None) -> int | float:
    if unit is None:
        return value

    factor = factors.get(unit, 1)
    return float(value) / factor


def parse_resource_spec(spec: str) -> ResourceDict:
    decoded = {
        match.group("key"): match.group("value") for match in resource_re.finditer(spec)
    }
    translated = {
        translations.get(key, key): decode_unit(value) for key, value in decoded.items()
    }

    return translated


def parse_resources(total: str, used: str) -> ResourcesDict:
    return {
        "total": default_resources | parse_resource_spec(total),
        "used": default_resources | parse_resource_spec(used),
    }


def extract_resource_group(resource: str) -> dict[str, Any]:
    if (match := generic_resource_re.match(resource)) is None:
        return {}

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
        name: converters.get(name, identity)(match.group(name))
        for name in ["type", "name", "quantity"]
    }

    return resource | modifier


def parse_generic_resource_spec(spec: str) -> list[GenericResourceDict]:
    if spec == "N/A":
        return []

    return [extract_resource_group(resource) for resource in spec.split(",")]
