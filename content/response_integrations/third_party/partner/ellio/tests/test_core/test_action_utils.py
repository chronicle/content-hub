from __future__ import annotations

from soar_sdk.SiemplifyDataModel import EntityTypes

from ...core.action_utils import collect_target_ips, is_public_ip


class FakeEntity:
    def __init__(self, identifier: str, entity_type: str = EntityTypes.ADDRESS,
                 is_internal: bool = False) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.is_internal = is_internal


class FakeSiemplify:
    def __init__(self, entities: list) -> None:
        self.target_entities = entities


def test_is_public_ip_accepts_global_addresses():
    assert is_public_ip("27.43.204.10")
    assert is_public_ip("2001:4860:4860::8888")


def test_is_public_ip_rejects_private_reserved_and_garbage():
    assert not is_public_ip("10.1.2.3")           # private
    assert not is_public_ip("127.0.0.1")          # loopback
    assert not is_public_ip("169.254.1.1")        # link-local
    assert not is_public_ip("192.0.2.10")         # RFC 5737 documentation range
    assert not is_public_ip("224.0.0.1")          # multicast
    assert not is_public_ip("ff02::1")            # IPv6 multicast
    assert not is_public_ip("not-an-ip")
    assert not is_public_ip("")
    assert not is_public_ip(None)


def test_collect_target_ips_filters_and_dedups():
    entities = [
        FakeEntity("27.43.204.10"),
        FakeEntity("10.0.0.5"),                            # private -> skipped
        FakeEntity("66.132.172.141", is_internal=True),    # SOAR-internal -> skipped
        FakeEntity("evil.example.net", entity_type=EntityTypes.HOSTNAME),  # ignored
    ]
    siemplify = FakeSiemplify(entities)
    target_ips, entity_by_ip, skipped = collect_target_ips(
        siemplify, "27.43.204.10, 91.191.209.46, 172.16.0.1")

    # entity + param dedup; the private param IP is reported skipped, not dropped
    assert target_ips == ["27.43.204.10", "91.191.209.46"]
    assert set(entity_by_ip) == {"27.43.204.10"}
    assert skipped == ["10.0.0.5", "66.132.172.141", "172.16.0.1"]


def test_collect_target_ips_empty_input():
    target_ips, entity_by_ip, skipped = collect_target_ips(FakeSiemplify([]), "")
    assert target_ips == []
    assert entity_by_ip == {}
    assert skipped == []


def test_collect_target_ips_none_param():
    target_ips, entity_by_ip, skipped = collect_target_ips(FakeSiemplify([]), None)
    assert target_ips == []
    assert entity_by_ip == {}
    assert skipped == []
