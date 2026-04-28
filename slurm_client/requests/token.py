import datetime as dt
import re
from dataclasses import dataclass
from typing import ClassVar, Self


@dataclass
class Token:
    token: str
    valid_until: dt.datetime

    token_expr_re: ClassVar[re.Pattern] = re.compile(r"SLURM_JWT=(.+)")

    @classmethod
    def from_expr(cls, expr: str, valid_until: dt.datetime) -> Self:
        match = cls.token_expr_re.fullmatch(expr)
        if match is None:
            raise ValueError(f"invalid token expression: {expr}")

        token = match.group(1)

        return cls(token, valid_until)

    def is_valid(self):
        now = dt.datetime.now(tz=dt.UTC)

        return now + dt.timedelta(seconds=1) < self.valid_until

    def __str__(self):
        return self.token
