from __future__ import annotations

import pytest

from ...core.action_utils import parse_account_input
from ...core.portnox_manager import flatten_device_for_enrichment, normalize_mac


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ("", []),
        ("user@example.com", ["user@example.com"]),
        ("a@example.com, b@example.com", ["a@example.com", "b@example.com"]),
        ('["a@example.com"]', ["a@example.com"]),
        ("['a@example.com','b@example.com']", ["a@example.com", "b@example.com"]),
        ("[None]", []),
        ("null", []),
    ],
)
def test_parse_account_input_returns_account_names(raw: str | None, expected: list[str]) -> None:
    assert parse_account_input(raw) == expected


@pytest.mark.parametrize("mac", ["00:1c:42:ab:cd:ef", "00-1C-42-AB-CD-EF", "001C.42AB.CDEF", "001C42ABCDEF"])
def test_normalize_mac_returns_bare_uppercase_hex(mac: str) -> None:
    assert normalize_mac(mac) == "001C42ABCDEF"


def test_flatten_device_for_enrichment_drops_empty_values() -> None:
    device = {
        "DeviceId": "device-1",
        "AllMacAddresses": ["001C42ABCDEF"],
        "AllIpAddresses": [],
        "_Account": {"AccountName": "user@example.com", "IsBlockByAdmin": True, "BlockReason": None},
    }

    assert flatten_device_for_enrichment(device) == {
        "Portnox_DeviceId": "device-1",
        "Portnox_AccountName": "user@example.com",
        "Portnox_IsBlockedByAdmin": True,
        "Portnox_MacAddresses": "001C42ABCDEF",
    }
