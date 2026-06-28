from dataclasses import dataclass
from typing import ClassVar

from textual.message import Message


class ConnectionEstablished(Message):
    pass


@dataclass
class FailedRequest(Message):
    context: ClassVar[str] = "Network error"
    reason: str


@dataclass
class FatalError(Message):
    context: ClassVar[str]
    reason: str

    def render(self):
        return "\n".join([self.context, "", f"[i]{self.reason}[/i]"])


@dataclass
class FailedSSHConnection(FatalError):
    context: ClassVar[str] = "Connecting to the ssh server failed:"
    reason: str


@dataclass
class FailedTokenCreation(FatalError):
    context: ClassVar[str] = "Failed to create a token:"
    reason: str
