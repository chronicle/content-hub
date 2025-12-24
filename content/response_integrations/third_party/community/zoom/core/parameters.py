from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Parameters:
    jwt_token: str
    account_id: str
    client_id: str
    client_secret: str

    @classmethod
    def from_conf(cls, conf: dict) -> Parameters:
        return cls(
            jwt_token=conf.get("JWT Token"),
            account_id=conf.get("Account ID"),
            client_id=conf.get("Client ID"),
            client_secret=conf.get("Client Secret"),
        )

    def as_dict(self):
        return asdict(self)
