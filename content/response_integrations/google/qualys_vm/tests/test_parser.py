from __future__ import annotations
import json
import os
import pytest
import xmltodict
from ..core.QualysVMParser import QualysVMParser

# Load mock data locally for unit tests
MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), "mock_data.json")
with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)


@pytest.fixture
def parser():
    return QualysVMParser()


def test_get_hosts_list_dict_single(parser):
    # Scenario A: Single host in dictionary format
    raw_data = {
        "HOST": {"IP": "1.1.1.1", "NETBIOS": "hostA", "DNS_DATA": {"HOSTNAME": "hostA"}}
    }
    hosts = parser._get_hosts_list(raw_data)
    assert len(hosts) == 1
    assert hosts[0]["IP"] == "1.1.1.1"
    assert hosts[0]["NETBIOS"] == "hostA"


def test_get_hosts_list_dict_multiple(parser):
    # Scenario B: Multiple hosts in a dictionary under list
    raw_data = {
        "HOST": [
            {"IP": "1.1.1.1", "NETBIOS": "hostA"},
            {"IP": "2.2.2.2", "NETBIOS": "hostB"},
        ]
    }
    hosts = parser._get_hosts_list(raw_data)
    assert len(hosts) == 2
    assert hosts[0]["IP"] == "1.1.1.1"
    assert hosts[1]["IP"] == "2.2.2.2"


def test_get_hosts_list_list_multiple(parser):
    # Scenario C: Multiple HOST_LIST blocks parsed as a list of dictionaries
    raw_data = [
        {"HOST": {"IP": "1.1.1.1", "NETBIOS": "hostA"}},
        {"HOST": {"IP": "2.2.2.2", "NETBIOS": "hostB"}},
    ]
    hosts = parser._get_hosts_list(raw_data)
    assert len(hosts) == 2
    assert hosts[0]["IP"] == "1.1.1.1"
    assert hosts[1]["IP"] == "2.2.2.2"


def test_get_hosts_list_list_direct(parser):
    # Scenario D: A list of host dictionaries directly
    raw_data = [
        {"IP": "1.1.1.1", "NETBIOS": "hostA"},
        {"IP": "2.2.2.2", "NETBIOS": "hostB"},
    ]
    hosts = parser._get_hosts_list(raw_data)
    assert len(hosts) == 2
    assert hosts[0]["IP"] == "1.1.1.1"
    assert hosts[1]["IP"] == "2.2.2.2"


def test_get_hosts_list_empty(parser):
    # Scenario E: Empty host list (None or empty list)
    assert parser._get_hosts_list(None) == []
    assert parser._get_hosts_list([]) == []


def test_get_ip_for_hostname(parser):
    raw_data = [
        {
            "HOST": {
                "IP": "192.168.1.6",
                "DNS_DATA": {"HOSTNAME": "agents-linux-machine"},
            }
        },
        {"HOST": {"IP": "192.168.1.12", "NETBIOS": "fluentd"}},
    ]
    # Test matching via DNS_DATA -> HOSTNAME
    assert parser.get_ip_for_hostname(raw_data, "agents-linux-machine") == "192.168.1.6"
    # Test matching via NETBIOS
    assert parser.get_ip_for_hostname(raw_data, "fluentd") == "192.168.1.12"
    # Test non-matching hostname
    assert parser.get_ip_for_hostname(raw_data, "non-existent") is None


def test_filter_hostname(parser):
    raw_data = [
        {
            "HOST": {
                "IP": "192.168.1.6",
                "DNS_DATA": {"HOSTNAME": "agents-linux-machine"},
            }
        },
        {"HOST": {"IP": "192.168.1.12", "NETBIOS": "fluentd"}},
    ]
    # Test matching single host via DNS_DATA
    res = parser.filter_hostname(raw_data, "agents-linux-machine")
    assert isinstance(res, dict)
    assert res["IP"] == "192.168.1.6"

    # Test matching single host via NETBIOS
    res2 = parser.filter_hostname(raw_data, "fluentd")
    assert isinstance(res2, dict)
    assert res2["IP"] == "192.168.1.12"


def test_get_detection_quids(parser):
    # Test dictionary detections
    raw_data_dict = {"HOST": {"DETECTION_LIST": {"DETECTION": {"QID": "6276533"}}}}
    assert parser.get_detection_quids(raw_data_dict) == ["6276533"]

    # Test list detections
    raw_data_list = {
        "HOST": {
            "DETECTION_LIST": {"DETECTION": [{"QID": "6276533"}, {"QID": "6277463"}]}
        }
    }
    assert parser.get_detection_quids(raw_data_list) == ["6276533", "6277463"]


def test_parser_with_real_v5_host_xml(parser):
    xml_content = MOCK_DATA.get("hosts_list_multiple_hosts")
    parsed = xmltodict.parse(xml_content, dict_constructor=dict)
    hosts = parsed.get("HOST_LIST_OUTPUT", {}).get("RESPONSE", {}).get("HOST_LIST", [])

    # Verify hosts resolution
    hosts_list = parser._get_hosts_list(hosts)
    assert len(hosts_list) == 2

    # Verify fallback hostname matching on DNS_DATA -> HOSTNAME
    assert parser.get_ip_for_hostname(hosts, "fluentd") == "192.168.1.12"
    assert parser.get_ip_for_hostname(hosts, "agents-linux-machine") == "192.168.1.6"


def test_parser_with_real_detections_xml(parser):
    xml_content = MOCK_DATA.get("detections_response")
    parsed = xmltodict.parse(xml_content, dict_constructor=dict)
    detections = (
        parsed.get("HOST_LIST_VM_DETECTION_OUTPUT", {})
        .get("RESPONSE", {})
        .get("HOST_LIST", [])
    )

    # Verify extracting detection QIDs from real list response
    quids = parser.get_detection_quids(detections)
    assert len(quids) > 0
    assert "980036" in quids


def test_parser_with_completely_empty_xml(parser):
    # Scenario: Completely empty host list from Qualys API (tag HOST_LIST is missing)
    xml_content = MOCK_DATA.get("hosts_list_completely_empty")
    parsed = xmltodict.parse(xml_content, dict_constructor=dict)
    hosts = parsed.get("HOST_LIST_OUTPUT", {}).get("RESPONSE", {}).get("HOST_LIST", [])

    # Verify raw parsed hosts is [] (default fallback)
    assert hosts == []

    # Verify hosts list normalizer returns []
    assert parser._get_hosts_list(hosts) == []

    # Verify hostname-to-IP resolution safely returns None instead of crashing
    assert parser.get_ip_for_hostname(hosts, "fluentd") is None

    # Verify hostname filtering safely returns [] instead of crashing
    assert parser.filter_hostname(hosts, "fluentd") == []

    # Verify extracting detection QIDs safely returns [] instead of crashing
    assert parser.get_detection_quids(hosts) == []
