from __future__ import annotations

import pathlib

from TIPCommon.types import SingleJson

from google_threat_intelligence.tests.common import get_json_file_content

NON_MALICIOUS_IP_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/non_malicious_ip.json"
)

MALICIOUS_IP_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/malicious_ip.json"
)

NON_MALICIOUS_URL_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/non_malicious_url.json"
)

NON_MALICIOUS_PRIVATE_URL_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/non_malicious_private_url.json"
)

MALICIOUS_URL_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/malicious_url.json"
)

MALICIOUS_PRIVATE_URL_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/malicious_private_url.json"
)

NON_MALICIOUS_FILE_HASH_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/non_malicious_file_hash.json"
)

MALICIOUS_FILE_HASH_RESPONSE = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/malicious_file_hash.json"
)

MALICIOUS_DOMAIN_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/malicious_domain.json"
)

NON_MALICIOUS_DOMAIN_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/non_malicious_domain.json"
)

DTM_ALERTS_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/dtm_alerts.json"
)

DTM_ALERT_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/dtm_alert.json"
)

DTM_MONITOR_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/dtm_list_monitors.json"
)

GTI_ALERTS_COMPREHENSIVE_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/gti_alerts_comprehensive.json"
)

GTI_ALERTS_DEFAULT_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/gti_alerts_default.json"
)


RELATED_ASSOCIATIONS_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/related_associations.json"
)

RELATED_ASSOCIATIONS_REPORTS_RESPONSE: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent
    / "data/related_associations_reports.json"
)

SDK_MOCK_DATA: SingleJson = get_def_file_content(
    json_file_path=pathlib.Path(__file__).parent.parent / "data/sdk_mock_data.json"
)

WIDGET_PATH_URL = "/api/v3/gtiwidget/someUrl"

WIDGET_URL_RESPONSE: SingleJson = {
    "data": {
        "id": "8.8.8.8",
        "url": f"https://www.virustotal.com{WIDGET_PATH_URL}",
        "detection_ratio": {"detections": 0, "total": 94},
        "type": "SOME TYPE",
        "found": True,
    }
}

EMPTY_HTML_RESPONSE: str = "<head></head><body></body>"
EMPTY_ESCAPED_HTML_RESPONSE: str = "&lt;head&gt;&lt;/head&gt;&lt;body&gt;&lt;/body&gt;"


INVALID_FILE_HASH_RESPONSE = {
    "error": {"code": "NotFoundError", "message": "Resource not found."}
}

IP_ADDRESS_COMMENTS_RESPONSE = {
    "data": [
        {
            "id": "i-10.0.0.26-3ad69150",
            "type": "comment",
            "links": {
                "self": "https://www.virustotal.com/api/v3/"
                "comments/i-10.0.0.26-3ad69150"
            },
            "attributes": {
                "tags": [],
                "text": "Test 2025-05-28 08:48:29 UTC+01",
                "date": 1748418523,
                "html": "Test 2025-05-28 08:48:29 UTC+01",
                "votes": {"positive": 0, "negative": 0, "abuse": 0},
            },
        },
    ]
}

URL_ADDRESS_COMMENTS_RESPONSE = {
    "data": [
        {
            "id": "u-057e8630c8880da8778b4f99e048933efb7cee"
            "9abdcf57fad89a7e7a2c7eae04-040938d1",
            "type": "comment",
            "links": {
                "self": "https://www.virustotal.com/api/v3/comments/"
                "u-057e8630c8880da8778b4f99e048933efb7cee"
                "9abdcf57fad89a7e7a2c7eae04-040938d1"
            },
            "attributes": {
                "date": 1747820108,
                "text": "Addming Comments from SecOps",
                "votes": {"positive": 0, "negative": 0, "abuse": 0},
                "html": "Addming Comments from SecOps",
                "tags": [],
            },
        },
    ]
}


def create_ip_error_response(ip: str) -> SingleJson:
    return {
        "error": {
            "code": "InvalidArgumentError",
            "message": f'IP "{ip}" is not a valid IP address pattern',
        }
    }


def create_url_error_response(encoded_url: str) -> SingleJson:
    return {
        "error": {"code": "NotFoundError", "message": f'URL "{encoded_url}" not found'}
    }


def create_domain_error_response(domain: str) -> SingleJson:
    return {
        "error": {
            "code": "InvalidArgumentError",
            "message": f"Domain \"b'{domain}'\" is not a valid domain pattern",
        }
    }


def create_asm_issue(
    issue_id: str,
    last_seen: str,
    pretty_name: str = "Open Port",
    first_seen: str | None = None,
) -> SingleJson:
    """Create an ASM issue as returned by the ASM issues search/details endpoints"""
    return {
        "id": issue_id,
        "pretty_name": pretty_name,
        "description": f"Description of {issue_id}",
        "severity": 2,
        "category": "network",
        "first_seen": first_seen or last_seen,
        "last_seen": last_seen,
        "details": {"proof": f"Proof of {issue_id}"},
        "entity_name": "example.com",
        "entity_type": "domain",
        "identifiers": [{"type": "domain", "name": "example.com"}],
    }


def create_asm_entity(name: str, entity_type: str = "Domain") -> SingleJson:
    """Create an ASM entity as returned by the ASM entities search endpoint"""
    return {
        "id": f"entity-{name}",
        "name": name,
        "type": entity_type,
        "issue_count": 1,
        "vuln_count": 0,
        "critical_or_high": False,
        "tags": [],
        "details": {"name": name},
    }
