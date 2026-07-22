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

import datetime
import re
from enum import Enum
from typing import Sequence, Mapping

from dateutil.relativedelta import relativedelta


INTEGRATION_NAME: str = "PaloAltoCortexXDR"
ADD_HASHES_TO_BLOCK_LIST_ACTION_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Hashes To Block List"
)
ENRICH_ENTITIES_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Enrich Entities"
GET_ENDPOINT_AGENT_REPORT_ACTION_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Get Endpoint Agent Report"
)
ISOLATE_ENDPOINT_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Isolate Endpoint"
PING_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
QUERY_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Query"
UNISOLATE_ENDPOINT_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Unisolate Endpoint"
RESOLVE_INCIDENT_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Resolve an Incident"
UPDATE_INCIDENT_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Update an Incident"
EXECUTE_XQL_SEARCH_ACTION_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Execute XQL Search"
GET_INCIDENT_DETAILS_ACTION_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Get Incident Details"
)
ADD_COMMENT_TO_INCIDENT_ACTION_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Comment To Incident"
)
SCAN_ENDPOINT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Scan Endpoint"
DOWNLOAD_FILE_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Download File"

ALERTS_DEFAULT_LIMIT: int = 1000
ALREADY_EXISTS_ERR_CODE: int = 500
ALREADY_EXISTS_ERR_MSG: str = (
    "All hashes have already been added to the allow or block list"
)
ID_NOT_FOUND: str = "incident not found"

PRODUCT: str = "Cortex XDR"
VENDOR: str = "PaloAltoCortexXDR"

XDR_CONNECTOR_SCRIPT_NAME: str = "Palo Alto Cortex XDR Connector"
DEFAULT_NAME: str = "Palo Alto Cortex XDR Incident"
DEFAULT_EVENT_NAME: str = "Palo Alto Cortex XDR Incident Artifact"
MAX_LIMIT: int = 1000
XQL_DEFAULT_LIMIT: int = 50
EMPTY_RESULT: int = 0
ALERTS_LIMIT: int = 100
DEFAULT_DAYS_BACKWARDS: int = 1
MAP_FILE: str = "map.json"
XQL_PENDING: str = "PENDING"
XQL_FAILED: str = "FAIL"
XQL_SUCCESS: str = "SUCCESS"
AGENT_ID_VALIDATION_REGEX: re.Pattern = re.compile(r"[0-9a-fA-F]{32}")
BATCH_SIZE: int = 100
INVALID_SEVERITY_RANK: int = -1

SUCCESS_STATUS: str = "COMPLETED_SUCCESSFULLY"
# ID Management
MAX_IDS_TO_STORE: int = 1000
EXISTING_IDS_KEY: str = "existing_ids"

# API Response Keys
API_NAME_KEY: str = "name"
API_SOURCE_KEY: str = "source"
API_DETECTION_TIMESTAMP_KEY: str = "detection_timestamp"
API_FW_MISC_KEY: str = "fw_misc"
API_EVENT_TIMESTAMP_KEY: str = "event_timestamp"
API_CREATION_TIME_KEY: str = "creation_time"
API_HOST_NAME_KEY: str = "host_name"
API_ENDPOINT_DATA_KEY: str = "endpoint_data"
API_ENDPOINT_KEY: str = "endpoint"
API_ENDPOINT_NAME_KEY: str = "endpoint_name"
API_AGENT_FQDN_KEY: str = "agent_fqdn"

# Event Keys
EVENT_TYPE_KEY: str = "event_type"

# alerts count limit
MIN_ALERTS_LIMIT: int = 1
MIN_RANGE_LIMIT: int = 0
MAX_RANGE_LIMIT: int = 100

NULL_VALUE: int = 0

LOWEST_INCIDENT_SEVERITY_TO_FETCH_NAME: str = "Lowest Incident Severity To Fetch"
LOWEST_ALERT_SEVERITY_TO_FETCH_NAME: str = "Lowest Alert Severity To Fetch"

ACTION_FILE_SHA256_KEY: str = "action_file_sha256"
FILE_SHA256_KEY: str = "File_sha256"
ACTION_REMOTE_IP_KEY: str = "action_remote_ip"
NETWORK_REMOTE_IP_KEY: str = "network_remote_ip"

UNKNOWN_INCIDENT_ID: str = "unknown"
NONE_AS_STRING: str = "None"
TRUE_AS_STRING: str = "true"

# Event Types
EVENT_TYPE_INCIDENT: str = "incident"
EVENT_TYPE_ALERT: str = "alert"
EVENT_TYPE_FILE: str = "file_artifact"
EVENT_TYPE_NETWORK: str = "network_artifact"

SYNC_INCIDENTS_JOB_NAME: str = "Sync Incidents"
SYNC_INCIDENTS_TIMEOUT_IN_MILLISECONDS: int = 1740000
SECOPS_CASE_TAG: str = "Palo Alto XDR Incident"
CASE_STATUS: str = "BOTH"
CASES_SYNC_LIMIT: int = 100
INCIDENTS_LIMIT: int = 100
MISSING_PERMISSIONS_ERROR: str = "forbidden"
JOB_SYNC_LIMIT: int = 100
INCREMENT_CASE_UPDATED_TIME_BY_MS: int = 1

XDR_RESOLVED_STATUSES: list[str] = [
    "resolved_true_positive",
    "resolved_known_issue",
    "resolved_duplicate",
    "resolved_false_positive",
    "resolved_other",
    "resolved_security_testing",
]

ENTITY_TYPE: int = 2
ALERT_ID_CONTEXT_PROPERTY: str = "Incident_ID"
ALERT_CLOSE_STATUS: str = "Close"

COMMENTS_MODIFICATION_TIME_FILTER: int = 1
XDR_COMMENT_PREFIX: str = "Palo Alto XDR Incident"
SECOPS_COMMENT_PREFIX: str = "Google SecOps:"
SECOPS_TAG_PREFIX: str = "Google SecOps: "
XDR_TAG_PREFIX: str = "Palo Alto XDR: "
MIN_TAG_LEN: int = 2
MAX_TAG_LEN: int = 256
CONTEXT_INCIDENT_ID_FIELD: str = "Incident_ID"

INCIDENTS_JOB_IDS_FILE_NAME: str = "xdr_incidents_ids.json"
INCIDENTS_JOB_IDS_DB_KEY: str = "xdr_incidents_ids"
SYNC_INCIDENTS_CONTEXT_IDENTIFIER: str = "SyncXDRIncidents"

FINISHED_STATUSES: list[str] = [
    "CANCELLED", "ABORTED", "EXPIRED", "COMPLETED_SUCCESSFULLY", "FAILED", "TIMEOUT"
]

XDR_STATUS_RESOLVED_FALSE_POSITIVE: str = "resolved_false_positive"
XDR_STATUS_RESOLVED_OTHER: str = "resolved_other"
XDR_STATUS_RESOLVED_KNOWN_ISSUE: str = "resolved_known_issue"
XDR_STATUS_RESOLVED_DUPLICATE: str = "resolved_duplicate"
XDR_STATUS_RESOLVED_TRUE_POSITIVE: str = "resolved_true_positive"
XDR_STATUS_RESOLVED_SECURITY_TESTING: str = "resolved_security_testing"
XDR_COMMENT: str = "comment"
XDR_INC_ID: str = "incident_id"

XDR_ALERTS_CONTEXT_KEY: str = "XDR_ALERTS"

REASON_MALICIOUS = "Malicious"
REASON_NOT_MALICIOUS = "NotMalicious"
REASON_INCONCLUSIVE = "Inconclusive"
REASON_MAINTENANCE = "Maintenance"

ROOT_CAUSE_KNOWN_ISSUE = "Known Issue"
ROOT_CAUSE_FALSE_POSITIVE = "False Positive"
ROOT_CAUSE_DUPLICATE_INCIDENT = "Duplicate Incident"
ROOT_CAUSE_NO_CLEAR_CONCLUSION = "No clear conclusion"
ROOT_CAUSE_OTHER = "Other"
ROOT_CAUSE_TRUE_POSITIVE = "True Positive"
ROOT_CAUSE_SECURITY_TESTING = "Security Testing"
ROOT_CAUSE_PENETRATION_TEST = "Penetration Test"

XDR_STATUS_TO_CLOSURE_REASONS_MAP: Mapping[str, tuple[str, ...]] = {
    XDR_STATUS_RESOLVED_KNOWN_ISSUE: (
        REASON_NOT_MALICIOUS,
        ROOT_CAUSE_KNOWN_ISSUE,
        REASON_NOT_MALICIOUS,
        ROOT_CAUSE_FALSE_POSITIVE,
    ),
    XDR_STATUS_RESOLVED_DUPLICATE: (
        REASON_INCONCLUSIVE,
        ROOT_CAUSE_DUPLICATE_INCIDENT,
        REASON_INCONCLUSIVE,
        ROOT_CAUSE_NO_CLEAR_CONCLUSION,
    ),
    XDR_STATUS_RESOLVED_FALSE_POSITIVE: (
        REASON_NOT_MALICIOUS,
        ROOT_CAUSE_FALSE_POSITIVE,
        REASON_NOT_MALICIOUS,
        ROOT_CAUSE_OTHER,
    ),
    XDR_STATUS_RESOLVED_OTHER: (
        REASON_INCONCLUSIVE,
        ROOT_CAUSE_NO_CLEAR_CONCLUSION,
        None,
        None,
    ),
    XDR_STATUS_RESOLVED_TRUE_POSITIVE: (
        REASON_MALICIOUS,
        ROOT_CAUSE_TRUE_POSITIVE,
        REASON_MALICIOUS,
        ROOT_CAUSE_OTHER,
    ),
    XDR_STATUS_RESOLVED_SECURITY_TESTING: (
        REASON_MAINTENANCE,
        ROOT_CAUSE_SECURITY_TESTING,
        REASON_NOT_MALICIOUS,
        ROOT_CAUSE_PENETRATION_TEST,
    ),
}


class CortexSortTypesEnum(Enum):
    SORT_BY_CREATION_TIME: str = "creation_time"
    SORT_BY_MODIFICATION_TIME: str = "modification_time"


class CortexSortOrderEnum(Enum):
    SORT_BY_ASC_ORDER: str = "asc"
    SORT_BY_DESC_ORDER: str = "desc"


class CortexCreationFilterEnum(Enum):
    GTE_CREATION_TIME: str = "gte"
    LTE_CREATION_TIME: str = "lte"


class CortexModificationFilterEnum(Enum):
    GTE_MODIFICATION_TIME: str = "gte"
    LTE_MODIFICATION_TIME: str = "lte"


class XDRPriorityEnum(Enum):
    CRITICAL: str = "critical"
    HIGH: str = "high"
    MED: str = "medium"
    LOW: str = "low"


class SiemplifyPriorityEnum(Enum):
    INFO: int = 0
    LOW: int = 40
    MEDIUM: int = 60
    HIGH: int = 80
    CRITICAL: int = 100


# Mappings
PRIORITIES_MAP: Mapping[str, int] = {
    "low": SiemplifyPriorityEnum.LOW.value,
    "medium": SiemplifyPriorityEnum.MEDIUM.value,
    "high": SiemplifyPriorityEnum.HIGH.value,
    "critical": SiemplifyPriorityEnum.CRITICAL.value,
}

SEVERITY_ORDER: list[str] = ["low", "medium", "high", "critical"]


POSSIBLE_TIMEFRAME_TO_HOURS_VALUES: Sequence[str] = [
    "Last Hour",
    "Last 6 Hours",
    "Last 24 Hours",
    "Last Week",
    "Last Month",
    "Custom",
]

POSSIBLE_STATUSES: list[str] = [
    "new",
    "under_investigation",
    "resolved_threat_handled",
    "resolved_known_issue",
    "resolved_duplicate",
    "resolved_false_positive",
    "resolved_other",
]

STATUS_MAPPING: Mapping[str, list[str]] = {
    "new": ["new"],
    "under investigation": ["under_investigation"],
    "resolved": [
        "resolved_threat_handled",
        "resolved_known_issue",
        "resolved_duplicate",
        "resolved_false_positive",
        "resolved_other",
    ],
}


class DDLEnum(Enum):
    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class TimeFrameDDLEnum(DDLEnum):
    LAST_HOUR: str = "Last Hour"
    LAST_6_HOURS: str = "Last 6 Hours"
    LAST_24_HOURS: str = "Last 24 Hours"
    LAST_WEEK: str = "Last Week"
    LAST_MONTH: str = "Last Month"
    CUSTOM: str = "Custom"

    def to_start_date(self) -> datetime.date:
        current_time: datetime.datetime = datetime.datetime.now()
        match self:
            case TimeFrameDDLEnum.LAST_HOUR:
                return current_time - datetime.timedelta(hours=1)
            case TimeFrameDDLEnum.LAST_6_HOURS:
                return current_time - datetime.timedelta(hours=6)
            case TimeFrameDDLEnum.LAST_24_HOURS:
                return current_time - datetime.timedelta(days=1)
            case TimeFrameDDLEnum.LAST_WEEK:
                return current_time - datetime.timedelta(days=7)
            case TimeFrameDDLEnum.LAST_MONTH:
                return current_time - relativedelta(months=1)
            case _:
                raise ValueError(
                    f"Cannot convert object {self} to Date object",
                )

WINDOWS_OS_TYPE: str = "windows"
LINUX_OS_TYPE: str = "linux"
MACOS_OS_TYPE: str = "macos"

ENDPOINT_ID_KEY: str = "endpoint_id"
FILE_PATH_KEY: str = "file_path"
GROUP_ID_KEY: str = "group_id"
STATUS_KEY: str = "status"
IDENTIFIER_KEY: str = "identifier"
LOCAL_PATH_KEY: str = "local_path"
DOWNLOAD_FILE_PATH_KEY: str = "download_file_path"
ERRORED_FILE_PATHS_KEY: str = "errored_file_paths"
OS_TYPE_KEY: str = "os_type"

PENDING_STATUS: str = "Pending"
