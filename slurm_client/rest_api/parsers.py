from typing import TypedDict

Infinite = object()


class ValueSet(TypedDict):
    set: bool
    infinite: bool
    number: int


def parse_value_set(x: ValueSet) -> int | None:
    if not x["set"]:
        return None
    if x["infinite"]:
        return Infinite

    return x["number"]
