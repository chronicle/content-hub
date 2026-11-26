from __future__ import annotations

import contextlib
import dataclasses
import json
from collections.abc import Iterator

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class PortnoxCloud:
    """In-memory stand-in for a Portnox Cloud tenant."""

    account_devices: list[SingleJson] = dataclasses.field(default_factory=list)
    accounts: set[str] = dataclasses.field(default_factory=set)
    groups: set[str] = dataclasses.field(default_factory=lambda: {"Default"})
    blocked_accounts: dict[str, str] = dataclasses.field(default_factory=dict)
    blocked_devices: dict[str, str] = dataclasses.field(default_factory=dict)
    account_groups: dict[str, str] = dataclasses.field(default_factory=dict)
    failure_status_code: int | None = None

    @contextlib.contextmanager
    def fail_requests(self, status_code: int = 500) -> Iterator[None]:
        self.failure_status_code = status_code
        try:
            yield
        finally:
            self.failure_status_code = None

    def add_device(self, account_name: str, device: SingleJson) -> None:
        self.accounts.add(account_name)
        for entry in self.account_devices:
            if entry["Account"]["AccountName"] == account_name:
                entry["Devices"].append(device)
                return
        self.account_devices.append({
            "Account": {"AccountName": account_name, "IsBlockByAdmin": False, "BlockReason": None},
            "Devices": [device],
        })

    def list_devices(self, filter_text: str | None, page_number: int, page_size: int) -> SingleJson:
        needle = (filter_text or "").lower()
        matches = [e for e in self.account_devices if needle in json.dumps(e).lower()]
        start = (page_number - 1) * page_size
        return {"Entities": matches[start : start + page_size], "TotalCount": len(matches)}

    def device_ids(self) -> set[str]:
        return {d["DeviceId"] for e in self.account_devices for d in e["Devices"]}

    def block_device(self, device_id: str, reason: str) -> bool:
        if device_id not in self.device_ids():
            return False
        self.blocked_devices[device_id] = reason
        return True

    def block_account(self, account_name: str, reason: str) -> bool:
        if account_name not in self.accounts:
            return False
        self.blocked_accounts[account_name] = reason
        return True

    def move_account_to_group(self, account_name: str, group_name: str) -> bool:
        if account_name not in self.accounts or group_name not in self.groups:
            return False
        self.account_groups[account_name] = group_name
        return True
