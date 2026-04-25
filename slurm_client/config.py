import datetime as dt
from dataclasses import dataclass


@dataclass
class Config:
    server: str
    address: str

    token_lifespan: dt.timedelta = dt.timedelta(minutes=15)
    ping_interval: float = 3.0
