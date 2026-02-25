"""Common utilities and constants for Silverfort tests."""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

from integration_testing.common import get_def_file_content  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")

# Load mock responses
MOCK_RESPONSES_FILE = pathlib.Path.joinpath(MOCKS_PATH, "responses.json")


def load_mock_responses() -> SingleJson:
    """Load mock responses from JSON file."""
    if MOCK_RESPONSES_FILE.exists():
        return json.loads(MOCK_RESPONSES_FILE.read_text(encoding="utf-8"))
    return {}


MOCK_DATA: SingleJson = load_mock_responses() if MOCK_RESPONSES_FILE.exists() else {}

# Default mock responses
MOCK_ENTITY_RISK: SingleJson = {
    "user_principal_name": "test.user@example.com",
    "risk_score": 65.0,
    "severity": "medium",
    "risk_factors": [
        {"type": "activity_risk", "severity": "medium", "description": "Suspicious activity"},
    ],
    "last_updated": "2026-01-13T10:00:00Z",
}

MOCK_SERVICE_ACCOUNT: SingleJson = {
    "guid": "82132169-b41b-8b47-ba4b-494814500785",
    "display_name": "svc_test",
    "upn": "svctest@ad.example.com",
    "dn": "CN=svc_test,CN=Users,DC=ad,DC=example,DC=com",
    "domain": "ad.example.com",
    "category": "machine_to_machine",
    "risk": "low",
    "predictability": "high",
    "protected": True,
    "sources_count": 5,
    "destinations_count": 3,
    "number_of_authentications": 1500,
}

MOCK_SERVICE_ACCOUNTS_LIST: SingleJson = {
    "service_accounts": [
        {
            "guid": "82132169-b41b-8b47-ba4b-494814500785",
            "display_name": "svc_test",
            "risk": "low",
        },
        {
            "guid": "4e9f7309-5a48-f542-8f2b-334f72cf2c89",
            "display_name": "svc_app",
            "risk": "medium",
        },
    ],
    "total_count": 2,
}

MOCK_SA_POLICY: SingleJson = {
    "enabled": True,
    "block": False,
    "send_to_siem": True,
    "risk_level": "medium",
    "allow_all_sources": False,
    "allow_all_destinations": False,
    "protocols": ["Kerberos", "ldap"],
    "allowed_sources": [{"key": "10.0.0.1", "key_type": "ip"}],
    "allowed_destinations": [{"key": "server.example.com", "key_type": "hostname"}],
}

MOCK_POLICY: SingleJson = {
    "policyId": "1",
    "policyName": "Test Policy",
    "enabled": True,
    "policyType": "authentication",
    "authType": "mfa",
    "protocols": ["Kerberos", "NTLM"],
    "action": "mfa",
    "MFAPrompt": "always",
    "allUsersAndGroups": False,
    "usersAndGroups": [
        {
            "identifierType": "upn",
            "identifier": "user@example.com",
            "displayName": "Test User",
            "domain": "example.com",
        }
    ],
    "allDevices": False,
    "sources": [],
    "allDestinations": False,
    "destinations": [
        {
            "identifierType": "hostname",
            "identifier": "server.example.com",
            "displayName": "Test Server",
            "domain": "example.com",
            "services": ["rdp"],
        }
    ],
}

MOCK_POLICIES_LIST: SingleJson = [
    {
        "policyId": "1",
        "policyName": "Test Policy 1",
        "enabled": True,
    },
    {
        "policyId": "2",
        "policyName": "Test Policy 2",
        "enabled": False,
    },
]

MOCK_RULES_NAMES_IDS: list[dict] = [
    {"id": "1", "name": "Test Policy 1"},
    {"id": "2", "name": "Test Policy 2"},
]
