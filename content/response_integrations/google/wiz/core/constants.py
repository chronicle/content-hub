# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaintenanceRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)

if TYPE_CHECKING:
    from collections.abc import AbstractSet, Mapping, Sequence


INTEGRATION_NAME: str = "Wiz"
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
GET_ISSUE_DETAILS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Issue Details"
GET_BLUE_AGENT_ANALYSIS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Get Blue Agent Analysis"
)
ADD_COMMENT_TO_ISSUE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Comment To Issue"
IGNORE_ISSUE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ignore Issue"
REOPEN_ISSUE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Reopen Issue"
RESOLVE_ISSUE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Resolve Issue"
LIST_RESOURCE_VULNERABILITY_FINDINGS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - List Resource Vulnerability Findings"
)

DEFAULT_MAX_FINDINGS: int = 100
MAX_FINDINGS_LIMIT: int = 500


ENDPOINTS: Mapping[str, str] = {
    "graphql": "/graphql",
}

DEFAULT_AUTH_URL: str = "https://auth.app.wiz.io"
AUTH_ENDPOINT: str = "/oauth/token"
AUTH_URL: str = f"{DEFAULT_AUTH_URL}{AUTH_ENDPOINT}"

STATUS_REJECTED: str = "REJECTED"

STATUS_REOPEN: str = "OPEN"

STATUS_RESOLVED: str = "RESOLVED"
DEFAULT_IGNORE_ISSUE_RESOLUTION_REASON: str = "False Positive"
IGNORE_ISSUE_RESOLUTION_REASONS: Mapping[str, str] = {
    "False Positive": "FALSE_POSITIVE",
    "Exception": "EXCEPTION",
    "Won't Fix": "WONT_FIX",
}
DEFAULT_RESOLVE_ISSUE_RESOLUTION_REASON: str = "Not Malicious Threat"
RESOLVE_ISSUE_RESOLUTION_REASONS: Mapping[str, str] = {
    "Malicious Threat": "MALICIOUS_THREAT",
    "Not Malicious Threat": "NOT_MALICIOUS_THREAT",
    "Security Test Threat": "SECURITY_TEST_THREAT",
    "Planned Action Threat": "PLANNED_ACTION_THREAT",
    "Inconclusive Threat": "INCONCLUSIVE_THREAT",
}
ISSUE_NOT_FOUND_ERRORS: Sequence[str] = ["id must be a valid service issue id"]
UNAUTHORIZED_STATUS_CODE: int = 401


SYNC_JOB_SCRIPT_NAME: str = "Wiz - Wiz and Google SecOps Bi-directional Sync Job"
SYNC_JOB_IDENTIFIER: str = "WizSecopsBidirectionalSyncJob"
UUID_LENGTH: int = 36
FALLBACK_TIMESTAMP: int = 0
MS_TO_SEC_DIVISOR: int = 1000

WIZ_SEVERITY_WEIGHTS: Mapping[str, int] = {
    "CRITICAL": 500,
    "HIGH": 400,
    "MEDIUM": 300,
    "LOW": 200,
    "INFORMATIONAL": 100,
}

SECOPS_PRIORITY_WEIGHTS: Mapping[str, int] = {
    "critical": 500,
    "high": 400,
    "medium": 300,
    "low": 200,
    "informational": 100,
    "info": 100,
}

WIZ_TO_SECOPS_PRIORITY: Mapping[str, str] = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
    "INFORMATIONAL": "Informational",
}

WIZ_CLOSED_STATUSES: AbstractSet[str] = {
    STATUS_RESOLVED,
    STATUS_REJECTED,
}

REASON_UNSPECIFIED: str = "REASON_UNSPECIFIED"

WIZ_REASON_FALSE_POSITIVE: str = "FALSE_POSITIVE"
WIZ_REASON_MALICIOUS_THREAT: str = "MALICIOUS_THREAT"
WIZ_REASON_NOT_MALICIOUS_THREAT: str = "NOT_MALICIOUS_THREAT"
WIZ_REASON_SECURITY_TEST_THREAT: str = "SECURITY_TEST_THREAT"
WIZ_REASON_PLANNED_ACTION_THREAT: str = "PLANNED_ACTION_THREAT"
WIZ_REASON_INCONCLUSIVE_THREAT: str = "INCONCLUSIVE_THREAT"

CLOSE_REASON_TO_WIZ_REASON: Mapping[str, str] = {
    "REASON_MALICIOUS": WIZ_REASON_MALICIOUS_THREAT,
    "MALICIOUS": WIZ_REASON_MALICIOUS_THREAT,
    "0": WIZ_REASON_MALICIOUS_THREAT,
    "REASON_NOT_MALICIOUS": WIZ_REASON_NOT_MALICIOUS_THREAT,
    "NOTMALICIOUS": WIZ_REASON_NOT_MALICIOUS_THREAT,
    "NOT_MALICIOUS": WIZ_REASON_NOT_MALICIOUS_THREAT,
    "NOT MALICIOUS": WIZ_REASON_NOT_MALICIOUS_THREAT,
    "1": WIZ_REASON_NOT_MALICIOUS_THREAT,
    "REASON_MAINTENANCE": WIZ_REASON_PLANNED_ACTION_THREAT,
    "MAINTENANCE": WIZ_REASON_PLANNED_ACTION_THREAT,
    "2": WIZ_REASON_PLANNED_ACTION_THREAT,
    "REASON_INCONCLUSIVE": WIZ_REASON_INCONCLUSIVE_THREAT,
    "INCONCLUSIVE": WIZ_REASON_INCONCLUSIVE_THREAT,
    "3": WIZ_REASON_INCONCLUSIVE_THREAT,
    "UNKNOWN": WIZ_REASON_INCONCLUSIVE_THREAT,
    "4": WIZ_REASON_INCONCLUSIVE_THREAT,
}

CLOSE_VERDICT_TO_WIZ_REASON: Mapping[int, str] = {
    1: WIZ_REASON_MALICIOUS_THREAT,
    2: WIZ_REASON_NOT_MALICIOUS_THREAT,
    3: WIZ_REASON_PLANNED_ACTION_THREAT,
    4: WIZ_REASON_INCONCLUSIVE_THREAT,
}

DEFAULT_SECOPS_CLOSURE: tuple[str, str] = (
    "Inconclusive",
    CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
)

WIZ_REASON_TO_SECOPS_CLOSURE: Mapping[str, tuple[str, str]] = {
    WIZ_REASON_MALICIOUS_THREAT: (
        "Malicious",
        CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
    ),
    WIZ_REASON_NOT_MALICIOUS_THREAT: (
        "NotMalicious",
        CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
    ),
    WIZ_REASON_FALSE_POSITIVE: (
        "NotMalicious",
        CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
    ),
    "EXCEPTION": (
        "NotMalicious",
        CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
    ),
    "WONT_FIX": (
        "NotMalicious",
        CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
    ),
    WIZ_REASON_PLANNED_ACTION_THREAT: (
        "Maintenance",
        CloseCaseOrAlertMaintenanceRootCauses.OTHER.value,
    ),
    WIZ_REASON_SECURITY_TEST_THREAT: (
        "Maintenance",
        CloseCaseOrAlertMaintenanceRootCauses.OTHER.value,
    ),
    WIZ_REASON_INCONCLUSIVE_THREAT: DEFAULT_SECOPS_CLOSURE,
}

SYNC_COMMENT_PREFIX: str = "[SecOps & Wiz Sync Job]"
WROTE_IN_SECOPS_SIGNATURE: str = " wrote in Google SecOps on "
WROTE_IN_WIZ_SIGNATURE: str = " wrote in Wiz on "
NOT_FOUND_INDEX: int = -1

WIZ_REOPENED_COMMENT_SUBSTRING: str = (
    "was reopened because the corresponding Wiz Threat status was updated to"
)
DEFAULT_FALLBACK_VALUE: int = 0
STATUS_CAPTURE_GROUP: int = 1
COLON_SPACE_OFFSET: int = 2
HOURS_BACK_24: int = 24
MS_TO_S_FACTOR: int = 1000

RETRY_TOTAL_ATTEMPTS: int = 5
RETRY_BACKOFF_FACTOR: int = 2
RETRY_STATUS_CODES: tuple[int, ...] = (429, 500, 502, 503, 504)
RETRY_ALLOWED_METHODS: tuple[str, ...] = (
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
    "HEAD",
)
PRODUCT_ALERTS_LIMIT: int = 50
MIN_HOURS_BACKWARDS: int = 1
MAX_HOURS_BACKWARDS: int = 720
