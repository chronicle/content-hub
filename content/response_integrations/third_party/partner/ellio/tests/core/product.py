from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class Ellio:
    """In-memory stand-in for the ELLIO API used by the action tests."""

    cti: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    cbs: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    blocklisted: list[SingleJson] = dataclasses.field(default_factory=list)

    def set_cti(self, ip: str, record: SingleJson) -> None:
        self.cti[ip] = record

    def get_cti(self, ip: str) -> SingleJson | None:
        return self.cti.get(ip)

    def set_cbs(self, ip: str, record: SingleJson) -> None:
        self.cbs[ip] = record

    def get_cbs(self, ip: str) -> SingleJson | None:
        return self.cbs.get(ip)

    def add_blocklist_rule(self, ip: str, body: SingleJson) -> SingleJson:
        self.blocklisted.append({"ip": ip, **body})
        return {"ip": ip, "status": "added"}
