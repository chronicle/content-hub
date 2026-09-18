from __future__ import annotations

import types

import pytest

from ...core.datamodels import (
    BaseModel,
    CustomList,
    DHCPLease,
    DNSRecord,
    DNSSecurityEvent,
    DossierJobResult,
    DossierWaitResult,
    Host,
    IndicatorIntelLookupResult,
    IndicatorThreatLookupTideResult,
    InfobloxIQForThreatDefense,
    InfobloxIQForThreatDefenseAsset,
    InfobloxIQForThreatDefenseDetails,
    InfobloxIQForThreatDefenseEvent,
    InfobloxIQForThreatDefenseIndicator,
    IPLookup,
    NetworkList,
    RecommendationActionResult,
    SecurityPolicy,
)


class FakeEnvironmentCommon:
    def get_environment(self, raw_data: dict) -> str:
        return "Default Environment"


def make_alert_info() -> types.SimpleNamespace:
    """A blank, attribute-settable stand-in for soar_sdk's AlertInfo."""
    return types.SimpleNamespace()


class TestBaseModel:
    @pytest.mark.parametrize(
        "severity,expected",
        [
            ("LOW", 40),
            ("low", 40),
            ("INFO", 40),
            ("MEDIUM", 60),
            ("HIGH", 80),
            ("CRITICAL", 100),
            ("UNKNOWN", 40),
            (None, 40),
            ("", 40),
        ],
    )
    def test_get_severity_mapping(self, severity, expected: int) -> None:
        assert BaseModel({}).get_severity(severity) == expected

    def test_to_json_returns_raw_data(self) -> None:
        raw = {"a": 1}
        assert BaseModel(raw).to_json() == raw

    def test_to_csv_flattens_json(self) -> None:
        result = BaseModel({"a": {"b": 1}}).to_csv()
        assert isinstance(result, dict)


class TestCustomList:
    def test_to_csv_maps_fields(self) -> None:
        model = CustomList({
            "id": 1,
            "name": "blocklist",
            "description": "desc",
            "confidence_level": "HIGH",
            "threat_level": "LOW",
            "item_count": 3,
        })
        assert model.to_csv() == {
            "Custom List ID": 1,
            "Name": "blocklist",
            "Description": "desc",
            "Confidence Level": "HIGH",
            "Threat Level": "LOW",
            "Item Count": 3,
        }

    def test_missing_fields_default_to_none(self) -> None:
        model = CustomList({})
        assert model.to_csv()["Custom List ID"] is None


class TestNetworkList:
    def test_to_csv_maps_fields(self) -> None:
        model = NetworkList({"id": 5, "name": "net1", "description": "d", "policy_id": 9})
        assert model.to_csv() == {
            "Network List ID": 5,
            "Name": "net1",
            "Description": "d",
            "Security Policy ID": 9,
        }


class TestDNSRecord:
    def test_to_csv_maps_fields(self) -> None:
        model = DNSRecord({
            "id": "r1",
            "absolute_name_spec": "host.example.com",
            "name_in_zone": "host",
            "type": "A",
            "ttl": 300,
            "updated_at": "2025-01-01T00:00:00Z",
            "disabled": False,
            "view_name": "default",
        })
        assert model.to_csv() == {
            "DNS ID": "r1",
            "Name In Zone": "host",
            "Absolute Name Spec": "host.example.com",
            "Type": "A",
            "TTL": 300,
            "Updated At": "2025-01-01T00:00:00Z",
            "Disabled": False,
            "View Name": "default",
        }


class TestIndicatorThreatLookupTideResult:
    def test_to_csv_uses_type_to_resolve_indicator_value(self) -> None:
        model = IndicatorThreatLookupTideResult({
            "type": "HOST",
            "host": "evil.example.com",
            "threat_level": "HIGH",
            "class": "Malware",
            "property": "Malware_C2",
            "profile": "IID",
            "detected": "2025-01-01T00:00:00Z",
        })
        assert model.to_csv() == {
            "Indicator": "evil.example.com",
            "Type": "HOST",
            "Threat Level": "HIGH",
            "Class": "Malware",
            "Property": "Malware_C2",
            "Profile": "IID",
            "Detected": "2025-01-01T00:00:00Z",
        }


class TestIndicatorIntelLookupResult:
    def test_to_csv_truncates_large_data(self) -> None:
        model = IndicatorIntelLookupResult({
            "params": {"source": "whois"},
            "status": "success",
            "data": {"x": "y" * 500},
            "time": "2025-01-01T00:00:00Z",
            "v": "1.0",
        })
        csv = model.to_csv()
        assert csv["Source"] == "whois"
        assert csv["Status"] == "success"
        assert csv["Time"] == "2025-01-01T00:00:00Z"
        assert csv["Version"] == "1.0"
        assert "[truncated]" in csv["Data"]


class TestIPLookup:
    def test_to_csv_extracts_nested_fields(self) -> None:
        model = IPLookup({
            "id": "ip1",
            "address": "10.0.0.5",
            "names": [{"name": "host1"}],
            "state": "used",
            "usage": ["DHCP"],
            "dhcp_info": {"client_hwaddr": "aa:bb:cc:dd:ee:ff"},
            "protocol": "ip4",
            "updated_at": "2025-01-01T00:00:00Z",
        })
        csv = model.to_csv()
        assert csv["Host Name"] == "host1"
        assert csv["Hardware Address"] == "aa:bb:cc:dd:ee:ff"
        assert csv["Address"] == "10.0.0.5"

    def test_to_csv_handles_missing_nested_fields(self) -> None:
        model = IPLookup({"id": "ip2", "address": "10.0.0.6"})
        csv = model.to_csv()
        assert csv["Host Name"] is None
        assert csv["Hardware Address"] is None


class TestInfobloxIQForThreatDefenseIndicator:
    def test_to_csv_joins_list_fields(self) -> None:
        model = InfobloxIQForThreatDefenseIndicator({
            "status": ["blocked"],
            "verified_assets": ["1.1.1.1"],
            "unverified_assets": [],
            "total_events": 5,
            "threat_level": "HIGH",
            "threat_indicator": "evil.com",
            "detected_at": "2025-01-01T00:00:00Z",
            "users": ["alice", "bob"],
            "description": "desc",
            "threat_actors": ["actor1"],
            "confidence_level": "HIGH",
            "first_detected": "2025-01-01T00:00:00Z",
            "last_detected": "2025-01-02T00:00:00Z",
        })
        csv = model.to_csv()
        assert csv["Status"] == "blocked"
        assert csv["Verified Assets"] == "1.1.1.1"
        assert csv["Unverified Assets"] == ""
        assert csv["Users"] == "alice, bob"
        assert csv["Threat Actors"] == "actor1"


class TestInfobloxIQForThreatDefenseEvent:
    def test_to_csv_maps_fields(self) -> None:
        model = InfobloxIQForThreatDefenseEvent({
            "threat_level": "HIGH",
            "threat_confidence": "HIGH",
            "policy": "default",
            "source": "feed1",
            "indicator": "evil.com",
            "actor_name": "actor1",
            "action": "block",
        })
        assert model.to_csv() == {
            "Threat Level": "HIGH",
            "Threat Confidence": "HIGH",
            "Policy": "default",
            "Source": "feed1",
            "Indicator": "evil.com",
            "Actor Name": "actor1",
            "Action": "block",
        }


class TestDossierResults:
    def test_dossier_wait_result_behaves_like_intel_lookup_result(self) -> None:
        model = DossierWaitResult({"params": {"source": "whois"}, "status": "success"})
        assert model.to_csv()["Source"] == "whois"

    def test_dossier_job_result_to_csv(self) -> None:
        model = DossierJobResult({"job_id": "job-1", "status": "PENDING"})
        assert model.to_csv() == {"Job ID": "job-1", "Status": "PENDING"}


class TestSecurityPolicy:
    def test_to_csv_defaults_missing_fields_to_empty_string(self) -> None:
        model = SecurityPolicy({})
        assert model.to_csv() == {
            "Security Policy ID": "",
            "Policy Name": "",
            "Description": "",
            "Default Action": "",
        }


class TestDHCPLease:
    def test_to_csv_maps_fields(self) -> None:
        model = DHCPLease({
            "address": "10.0.0.5",
            "hostname": "host1",
            "hardware": "aa:bb:cc:dd:ee:ff",
            "state": "active",
            "type": "dynamic",
            "starts": "2025-01-01T00:00:00Z",
            "ends": "2025-01-02T00:00:00Z",
            "fingerprint": "fp",
            "last_updated": "2025-01-01T00:00:00Z",
        })
        csv = model.to_csv()
        assert csv["Address"] == "10.0.0.5"
        assert csv["Type"] == "dynamic"


class TestInfobloxIQForThreatDefenseAsset:
    def test_to_csv_joins_lists_and_defaults_missing_to_empty(self) -> None:
        model = InfobloxIQForThreatDefenseAsset({})
        csv = model.to_csv()
        assert csv["IP Addresses"] == ""
        assert csv["MAC Addresses"] == ""
        assert csv["Users"] == ""
        assert csv["Indicators"] == ""

    def test_to_csv_with_values(self) -> None:
        model = InfobloxIQForThreatDefenseAsset({
            "ip_address": ["10.0.0.1"],
            "mac_address": ["aa:bb:cc:dd:ee:ff"],
            "users": ["alice"],
            "description": "desc",
            "device_name": "device1",
            "indicators": ["evil.com"],
            "is_risky": True,
        })
        csv = model.to_csv()
        assert csv["IP Addresses"] == "10.0.0.1"
        assert csv["Is Risky?"] is True


class TestInfobloxIQForThreatDefenseDetails:
    def test_to_csv_joins_threat_actors_by_name(self) -> None:
        model = InfobloxIQForThreatDefenseDetails({
            "insight_id": "insight-1",
            "name": "Insight One",
            "threat_properties": ["prop1"],
            "threat_actors": [{"actor_name": "actor1"}, {"actor_name": "actor2"}],
        })
        csv = model.to_csv()
        assert csv["Threat Actors"] == "actor1, actor2"
        assert csv["Threat Properties"] == "prop1"
        assert csv["Insight ID"] == "insight-1"


class TestRecommendationActionResult:
    def test_to_csv_maps_fields(self) -> None:
        model = RecommendationActionResult({
            "action": "Yes",
            "status": "success",
            "reason": None,
            "message": "Applied",
            "audit_entry_id": "audit-1",
        })
        assert model.to_csv() == {
            "Action": "Yes",
            "Status": "success",
            "Reason": None,
            "Message": "Applied",
            "Audit Entry ID": "audit-1",
        }


class TestHost:
    def test_to_csv_extracts_first_address(self) -> None:
        model = Host({
            "id": "h1",
            "name": "host1",
            "addresses": [{"address": "10.0.0.5", "space": "default"}],
            "comment": "note",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
            "tags": {"env": "prod"},
        })
        csv = model.to_csv()
        assert csv["IP Address"] == "10.0.0.5"
        assert csv["Space"] == "default"

    def test_to_csv_handles_no_addresses(self) -> None:
        model = Host({"id": "h2", "name": "host2"})
        csv = model.to_csv()
        assert csv["IP Address"] is None
        assert csv["Space"] is None


class TestDNSSecurityEvent:
    def test_event_id_is_deterministic_composite_key(self) -> None:
        raw = {
            "event_time": "2025-01-01T00:00:00Z",
            "qname": "some-very-long-domain-name.example.com",
            "device": "device1",
            "feed_name": "feed1",
        }
        model = DNSSecurityEvent(raw)
        assert model.event_id == "2025-01-01T00:00:00Z|some-very-long-domai|device1|feed1"

    def test_event_id_skips_missing_fields(self) -> None:
        model = DNSSecurityEvent({"event_time": "2025-01-01T00:00:00Z"})
        assert model.event_id == "2025-01-01T00:00:00Z"

    def test_get_alert_info_populates_fields(self) -> None:
        raw = {
            "event_time": "2025-01-01T00:00:00.000Z",
            "qname": "evil.example.com",
            "device": "device1",
            "feed_name": "feed1",
            "tclass": "Malware",
            "tfamily": "Trojan",
            "policy_name": "default",
            "severity": "HIGH",
        }
        model = DNSSecurityEvent(raw)
        alert_info = model.get_alert_info(make_alert_info(), FakeEnvironmentCommon(), "device_product_field")

        assert alert_info.environment == "Default Environment"
        assert alert_info.display_id == model.event_id
        assert alert_info.ticket_id == model.event_id
        assert alert_info.name == "Malware - evil.example.com"
        assert "Malware" in alert_info.description
        assert alert_info.device_vendor == "Infoblox"
        assert alert_info.priority == 80
        assert alert_info.extensions == alert_info.events[0]

    def test_get_alert_info_default_name_when_fields_missing(self) -> None:
        model = DNSSecurityEvent({"event_time": "2025-01-01T00:00:00.000Z"})
        alert_info = model.get_alert_info(make_alert_info(), FakeEnvironmentCommon(), "device_product_field")
        assert alert_info.name == "Infoblox DNS Security Event"


class TestInfobloxIQForThreatDefense:
    def test_event_id_defaults_to_insight_id(self) -> None:
        model = InfobloxIQForThreatDefense({"insight_id": "insight-1"})
        assert model.event_id == "insight-1"

    def test_get_alert_info_populates_fields(self) -> None:
        raw = {
            "insight_id": "insight-1",
            "name": "Insight One",
            "description": "desc",
            "severity": "CRITICAL",
            "evaluation_start_date": "2025-01-01T00:00:00.000Z",
            "evaluation_end_date": "2025-01-02T00:00:00.000Z",
        }
        model = InfobloxIQForThreatDefense(raw)
        alert_info = model.get_alert_info(make_alert_info(), FakeEnvironmentCommon(), "device_product_field")

        assert alert_info.display_id == "insight-1"
        assert alert_info.ticket_id == "insight-1"
        assert alert_info.name == "Insight One"
        assert alert_info.description == "desc"
        assert alert_info.priority == 100
        assert alert_info.source_grouping_identifier == "insight-1"
