from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial
from typing import Any, Literal, Self

from textual.message import Message


@dataclass
class Request:
    method: Literal["get", "post"]
    path: str
    parameters: dict[str, Any]
    response_parser: Callable[Message, [dict[str, Any]]]

    def path_parameters(self, **kwargs) -> Self:
        new_path = self.path.format(version="{version}", **kwargs)
        return replace(self, path=new_path)

    def parser_parameters(self, **kwargs) -> Self:
        new_parser = partial(self.response_parser, **kwargs)

        return replace(self, response_parser=new_parser)


def _decorator(method: str, path: str, parameters: dict[str, Any] = None):
    if parameters is None:
        parameters = {}

    def inner(func: Callable) -> Request:
        return Request(method, path, parameters, func)

    return inner


class _RequestSelector:
    def __getattr__(self, attr):
        if attr not in {"get", "post", "delete"}:
            return super().__getattr__(attr)

        return partial(_decorator, attr)


request = _RequestSelector()
