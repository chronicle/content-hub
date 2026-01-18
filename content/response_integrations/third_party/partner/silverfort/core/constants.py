"""Constants for Silverfort integration."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    pass

# Integration Identifiers
INTEGRATION_IDENTIFIER: str = "Silverfort"
INTEGRATION_DISPLAY_NAME: str = "Silverfort Identity Security"

# Script Identifiers
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
GET_ENTITY_RISK_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Get Entity Risk"
UPDATE_ENTITY_RISK_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Update Entity Risk"
GET_SERVICE_ACCOUNT_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Get Service Account"
LIST_SERVICE_ACCOUNTS_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - List Service Accounts"
UPDATE_SA_POLICY_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Update SA Policy"
GET_POLICY_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Get Policy"
UPDATE_POLICY_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Update Policy"
CHANGE_POLICY_STATE_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Change Policy State"
LIST_POLICIES_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - List Policies"

# Default Configuration Parameter Values
DEFAULT_VERIFY_SSL: bool = True
DEFAULT_PAGE_SIZE: int = 50
DEFAULT_PAGE_NUMBER: int = 1

# API Constants
API_KEY_HEADER: str = "X-Console-API-Key"
AUTHORIZATION_HEADER: str = "Authorization"
CONTENT_TYPE_HEADER: str = "Content-Type"
APPLICATION_JSON: str = "application/json"

# JWT Configuration
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_SECONDS: int = 3600  # 1 hour

# API Endpoints
ENDPOINTS: Mapping[str, str] = {
    # Risk API
    "get_entity_risk": "/v1/public/getEntityRisk",
    "update_entity_risk": "/v1/public/updateEntityRisk",
    # Service Accounts API
    "get_service_account": "/v1/public/serviceAccounts/{guid}",
    "add_service_account": "/v1/public/serviceAccounts/{guid}",
    "update_service_account": "/v1/public/serviceAccounts/update/{guid}",
    "remove_service_account": "/v1/public/serviceAccounts/remove/{guid}",
    "get_sa_policy": "/v1/public/serviceAccounts/policy/{guid}",
    "update_sa_policy": "/v1/public/serviceAccounts/policy/{guid}",
    "list_service_accounts": "/v1/public/serviceAccounts/index",
    "get_sa_guids": "/v1/public/serviceAccounts/guids",
    # Policies API v1
    "change_policy_state": "/v1/public/changePolicyState",
    "get_rules_name_and_status": "/v1/public/getRulesNameAndStatus",
    "get_rules_names_and_ids": "/v1/public/getRulesNamesAndIds",
    # Policies API v2
    "get_policy": "/v2/public/policies/{policy_id}",
    "update_policy": "/v2/public/policies/{policy_id}",
    "list_policies": "/v2/public/policies/index",
}

# Timeouts
REQUEST_TIMEOUT: int = 30


class ApiType(str, Enum):
    """Enum for Silverfort API types."""

    RISK = "risk"
    SERVICE_ACCOUNTS = "service_accounts"
    POLICIES = "policies"


class RiskSeverity(str, Enum):
    """Enum for risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(str, Enum):
    """Enum for risk types that can be updated."""

    ACTIVITY_RISK = "activity_risk"
    MALWARE_RISK = "malware_risk"
    DATA_BREACH_RISK = "data_breach_risk"
    CUSTOM_RISK = "custom_risk"


class ServiceAccountCategory(str, Enum):
    """Enum for service account categories."""

    MACHINE_TO_MACHINE = "machine_to_machine"
    INTERACTIVE = "interactive"
    UNKNOWN = "unknown"


class SAPolicyRiskLevel(str, Enum):
    """Enum for service account policy risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SAProtocol(str, Enum):
    """Enum for service account protocols."""

    KERBEROS = "Kerberos"
    LDAP = "ldap"
    NTLM = "ntlm"


# Service Account Index Fields
SA_INDEX_FIELDS: list[str] = [
    "guid",
    "display_name",
    "sources_count",
    "destinations_count",
    "number_of_authentications",
    "risk",
    "predictability",
    "protected",
    "upn",
    "dn",
    "spn",
    "comment",
    "owner",
    "type",
    "domain",
    "category",
    "creation_date",
    "highly_privileged",
    "interactive_login",
    "broadly_used",
    "suspected_brute_force",
    "repetitive_behavior",
]

# Policy Index Fields
POLICY_INDEX_FIELDS: list[str] = [
    "enabled",
    "policyName",
    "authType",
    "protocols",
    "policyType",
    "allUsersAndGroups",
    "usersAndGroups",
    "allDevices",
    "sources",
    "allDestinations",
    "destinations",
    "action",
    "MFAPrompt",
    "all",
    "bridgeType",
]
