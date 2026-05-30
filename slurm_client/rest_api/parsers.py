import datetime as dt
from typing import Literal, TypedDict

Infinite = object()


class ValueSet(TypedDict):
    set: bool
    infinite: bool
    number: int


def parse_value_set(x: ValueSet) -> int | None | Literal[Infinite]:
    if not x["set"]:
        return None
    if x["infinite"]:
        return Infinite

    return x["number"]


def parse_datetime(x: ValueSet) -> dt.datetime:
    value = parse_value_set(x)

    if not isinstance(value, int):
        value = 0

    return dt.datetime.fromtimestamp(value, dt.UTC)
