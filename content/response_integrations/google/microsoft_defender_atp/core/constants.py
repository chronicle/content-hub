# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from TIPCommon.types import SingleJson


AVAILABLE_STATUSES = ["Unknown", "New", "InProgress", "Resolved"]
AVAILABLE_SEVERITIES: list[str] = [
    "UnSpecified",
    "Informational",
    "Low",
    "Medium",
    "High",
    "Critical"
]

PROVIDER_NAME = "MicrosoftDefenderATP"
CREATE_ISOLATE_MACHINE_TASK_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Create Isolate Machine Task"
)
CREATE_RUN_ANTIVIRUS_SCAN_TASK_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Create Run Antivirus Scan Task"
)
CREATE_STOP_AND_QUARANTINE_FILE_SPECIFIC_MACHINE_TASK_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Create Stop and Quarantine a File on Specific Machine Task"
)
CREATE_UNISOLATE_MACHINE_TASK_SCRIPT_NAME: str = (
    f"{PROVIDER_NAME} - Create Unisolate Machine Task"
)
DELETE_ENTITY_INDICATORS_SCRIPT_NAME = f"{PROVIDER_NAME} - Delete Entity Indicators"
ENRICH_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich Entities"
GET_CURRENT_TASK_STATUS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Current Task Status"
GET_FILE_RELATED_ALERTS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get File Related Alerts"
GET_FILE_RELATED_MACHINES_SCRIPT_NAME = f"{PROVIDER_NAME} - Get File Related Machines"
GET_MACHINE_LOGON_USERS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Machine Logon Users"
GET_MACHINE_RELATED_ALERTS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Machine Related Alerts"
GET_MACHINE_VULNERABILITIES_SCRIPT_NAME: str = (
    f"{PROVIDER_NAME} - Get Machine Vulnerabilities"
)
LIST_ALERTS_SCRIPT_NAME = f"{PROVIDER_NAME} - List Alerts"
LIST_INDICATORS_SCRIPT_NAME = f"{PROVIDER_NAME} - List Indicators"
LIST_MACHINES_SCRIPT_NAME = f"{PROVIDER_NAME} - List Machines"
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
RUN_ADVANCED_HUNTING_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Run Advanced Hunting Query"
SUBMIT_ENTITY_INDICATORS_SCRIPT_NAME = f"{PROVIDER_NAME} - Submit Entity Indicators"
UPDATE_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Update Alert"
WAIT_TASK_STATUS_SCRIPT_NAME = f"{PROVIDER_NAME} - Wait for Task Status"
EXECUTE_LIVE_RESPONSE_COMMAND_SCRIPT_NAME: str = (
    f"{PROVIDER_NAME} - Execute Live Response Command"
)
GET_USER_RELATED_ALERTS_SCRIPT_NAME: str = f"{PROVIDER_NAME} - Get User Related Alerts"

GET_MACHINE_RECOMMENDATIONS_SCRIPT_NAME: str = (
    f"{PROVIDER_NAME} - Get Machine Recommendations"
)
LOGIN_API_ROOT_DEFAULT = "https://login.microsoftonline.com"
DEFAULT_ALERTS_LIMIT: int = 100
DEFAULT_MAX_ALERTS_TO_RETURN: int = 100
MIN_ALERTS_LIMITS_TO_RETURN: int = 1
DEFAULT_VENDOR_NAME = "Microsoft"
GRAPH_VENDOR: str = "AlertV2"
DEFAULT_PRODUCT_NAME = "Microsoft Defender ATP"
PRODUCT_NAME_V2: str = "MicrosoftDefenderATP"

STORED_IDS_LIMIT = 3000

ACTION_PARAM_MAPPING = {
    "Block": "Block",
    "Audit": "Audit",
    "Block And Remediate": "BlockAndRemediate",
    "Allow": "Allowed",
}

SHA256_LENGTH = 64
MD5_LENGTH = 32
SHA1_LENGTH = 40

CUSTOM_ACCESS_TOKEN_URL = "{login_api_root}/{tenant_id}/oauth2/token"
MIN_VULNERABILITIES_TO_RETURN: int = 1
MAX_VULNERABILITIES_TO_RETURN: int = 100

POSSIBLE_INDICATOR_TYPES = [
    "FileSha1",
    "FileSha256",
    "FileMd5",
    "CertificateThumbprint",
    "IpAddress",
    "DomainName",
    "Url",
]
POSSIBLE_ACTION_TYPES = [
    "Warn",
    "Block",
    "Audit",
    "Alert",
    "AlertAndBlock",
    "BlockAndRemediate",
    "Allowed",
]
POSSIBLE_SEVERITIES: list[str] = ["Informational", "Low", "Medium", "High", "Critical"]
SUCCESS_STATUSES: list[str] = ["Completed", "Succeeded"]
FINISHED_STATUSES: list[str] = SUCCESS_STATUSES + ["Failed"]
API_LIMIT_STATUS_CODE = 429
MIN_RECOMMENDATIONS: int = 1
MAX_RECOMMENDATIONS: int = 100
INTEGRATION_IDENTIFIER: str = "Microsoft Defender for Endpoint"
SEVERITY_MAPPING: SingleJson = {
    "UnSpecified": 0,
    "Informational": 1,
    "Low": 2,
    "Medium": 3,
    "High": 4,
    "Critical": 5,
}
POSSIBLE_SORT_ORDER: list[str] = ["asc", "desc"]

POSSIBLE_THREATS: list[str] = [
    "Associated Active Alert",
    "Exploit is available",
    "Exploit is verified",
    "This exploit is part of an exploit kit",
]

THREAT_QUERY_MAPPING: SingleJson = {
    "Associated Active Alert": "IsThreatActive",
    "Exploit is available": "HasExploit",
    "Exploit is verified": "IsExploitVerified",
    "This exploit is part of an exploit kit": "IsInExploitKit",
}

POSSIBLE_SORT_BY: list[str] = ["First Detection Time", "Severity", "Update Time"]

VALUES: str = "value"
DESC_SORT_ORDER: str = "desc"
SEVERITY: str = "severity"
DEFAULT_MAX_VULNERABILITIES: int = 100
DEFAULT_SORT_ORDER: str = "ASC"
THREAT_ATTRIBUTE_MAPPING: SingleJson = {
    "Associated Active Alert": "is_threat_active",
    "Exploit is available": "has_exploit",
    "Exploit is verified": "exploit_verified",
    "This exploit is part of an exploit kit": "exploit_in_kit",
}
SORT_KEY_MAPPING: SingleJson = {
    "First Detection Time": lambda v: v.published_on or "",
    "Severity": lambda v: SEVERITY_MAPPING.get(str(v.severity).title(), 0),
    "Update Time": lambda v: v.updated_on or "",
}

DEFAULT_SORT_BY: str = "Severity"
GRAPH_STATUS_MAPPING: dict[str, str] = {
    "InProgress": "inProgress",
    "Resolved": "resolved",
    "New": "new",
}
GRAPH_SEVERITY_MAPPING: dict[str, str] = {
    "Informational": "informational",
    "Low": "low",
    "Medium": "medium",
    "High": "high",
}

GRAPH_CLASSIFICATIONS_MAPPING: dict[str, str] = {
    "Unknown": "unknown",
    "FalsePositive": "falsePositive",
    "TruePositive": "truePositive",
}

GRAPH_DETERMINATIONS_MAPPING: dict[str, str] = {
    "NotAvailable": "notAvailable",
    "MultiStagedAttack": "multiStagedAttack",
    "MaliciousUserActivity": "maliciousUserActivity",
    "Malware": "malware",
    "CompromisedAccount": "compromisedAccount",
    "Phishing": "phishing",
    "UnwantedSoftware": "unwantedSoftware",
    "SecurityTesting": "securityTesting",
    "LineOfBusinessApplication": "lineOfBusinessApplication",
    "ConfirmedActivity": "confirmedActivity",
    "NotMalicious": "notMalicious",
    "Other": "other",
}

GRAPH_VALID_PAIRS: dict[str, list[str]] = {
    "truePositive": [
        "malware",
        "phishing",
        "compromisedAccount",
        "maliciousUserActivity",
        "multiStagedAttack",
        "unwantedSoftware",
        "other",
    ],
    "falsePositive": ["notMalicious", "other"],
}
