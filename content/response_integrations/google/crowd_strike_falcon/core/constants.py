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
from datetime import timedelta
from enum import Enum
from collections import namedtuple
from collections.abc import Mapping

from soar_sdk.SiemplifyDataModel import EntityTypes


INTEGRATION_NAME = "CrowdStrikeFalcon"
DEFAULT_DEVICE_VENDOR = "CrowdStrike"
PRODUCT_NAME = "Crowdstrike Falcon"
VENDOR_NAME = "Crowd Strike Falcon"
PROVIDER_NAME = "Crowd Strike Falcon"
SIEMPLIFY_PREFIX_FOR_APP = "siemplify"

API_ENDPOINTS = {
    "fetch_token": "oauth2/token",
    "queries_devices": "devices/queries/devices/v1",
    "queries_hidden_devices": "devices/queries/devices-hidden/v1",
    "entities_devices": "devices/entities/devices/v2",
    "user_uuids": "users/queries/user-uuids-by-email/v1",
    "detections": "detects/entities/detects/v2",
    "discover_streams": "sensors/entities/datafeed/v2",
    "ioc_endpoint": "indicators/entities/iocs/v1",
    "update_ioc": "iocs/entities/indicators/v1",
    "delete_ioc": "iocs/entities/indicators/v1",
    "get_ioc_id": "iocs/queries/indicators/v1",
    "get_alerts": "alerts/queries/alerts/v2",
    "get_alerts_details": "alerts/entities/alerts/v2",
    "detections_connector": "detects/queries/detects/v1",
    "detection_details": "detects/entities/summaries/GET/v1",
    "ioc_queries": "indicators/queries/devices/v1",
    "devices_actions": "devices/entities/devices-actions/v2",
    "ioc_listing": "indicators/queries/iocs/v1",
    "queries_processes": "indicators/queries/processes/v1",
    "entities_processes": "processes/entities/processes/v1",
    "vulnerability_ids": "spotlight/queries/vulnerabilities/v1",
    "vulnerability_details": "spotlight/entities/vulnerabilities/v2",
    "remediation_details": "spotlight/entities/remediations/v2",
    "create_session": "/real-time-response/entities/sessions/v1",
    "start_session": "real-time-response/combined/batch-init-session/v1",
    "responder_command": "real-time-response/entities/active-responder-command/v1",
    "responder_command_admin": "real-time-response/entities/admin-command/v1",
    "pull_file_from_host": "real-time-response/combined/batch-get-command/v1",
    "retrieve_get_command_status": "real-time-response/combined/batch-get-command/v1",
    "file_content": "real-time-response/entities/extracted-file-contents/v1",
    "get_iocs": "iocs/entities/indicators/v1",
    "upload_ioc": "iocs/entities/indicators/v1",
    "get_host_groups": "devices/combined/host-groups/v1",
    "get_devices_login_histories": "/devices/combined/devices/login-history/v1",
    "get_devices_online_states": "/devices/entities/online-state/v1",
    "update_alert": "/alerts/entities/alerts/v2/",
    "update_alerts": "/alerts/entities/alerts/v3",
    "upload_file": "/samples/entities/samples/v2/",
    "submit_for_analysis": "/falconx/entities/submissions/v1",
    "filter_submissions": "/falconx/queries/submissions/v1/",
    "get_submissions": "/falconx/entities/submissions/v1/",
    "get_submission_reports": "/falconx/entities/report-summaries/v1/",
    "upload_archive": "/archives/entities/archives/v2",
    "extract_archive": "/archives/entities/extractions/v1",
    "get_archive": "/archives/entities/archives/v1",
    "check_incident_exists": "/incidents/entities/incidents/GET/v1",
    "add_incident_comment": "/incidents/entities/incident-actions/v1",
    "update_incident": "/incidents/entities/incident-actions/v1",
    "search_user": "/user-management/queries/users/v1",
    "get_user_name": "/user-management/queries/users/v1",
    "get_incidents": "/incidents/queries/incidents/v1",
    "get_incidents_details": "/incidents/entities/incidents/GET/v1",
    "get_incident_behaviors": "/incidents/queries/behaviors/v1",
    "get_incident_behaviors_details": "/incidents/entities/behaviors/GET/v1",
    "on_demand_scan": "/ods/entities/scans/v1",
    "query_jobs": "/humio/api/v1/repositories/{repo_value}/queryjobs",
    "query_scans": "ods/queries/scans/v1",
}

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
UPDATE_DETECTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Detection"
CLOSE_DETECTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Close Detection"
LIST_HOSTS_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - List Hosts"
UPDATE_IOC_INFORMATION_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - Update IOC Information"
GET_HOSTS_BY_IOC_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - Get Hosts By IOC"
LIFT_CONTAINED_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Lift Contained Endpoint"
CONTAIN_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Contain Endpoint"
GET_HOST_INFORMATION_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - Get Host Information"
UPLOAD_IOCS_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - UploadIOCs"
ADD_COMMENT_TO_DETECTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment to Detection"
DELETE_IOC_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - Delete IOC"
LIST_UPLOADED_IOCS_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - List Uploaded IOCs"
GET_PROCESS_NAME_BY_IOC_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - Get Process By IOC"
LIST_HOST_VULNERABILITIES_SCRIPT_NAME = f"{DEFAULT_DEVICE_VENDOR} - List Host Vulnerabilities"
EXECUTE_COMMAND_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Command"
DOWNLOAD_FILE_FROM_HOSTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download File"
GET_EVENT_OFFSET_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Event Offset"
UPDATE_IDENTITY_PROTECTION_DETECTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Identity Protection Detection"
SUBMIT_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Submit File"
SUBMIT_URL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Submit URL"
ADD_INCIDENT_COMMENT_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Incident Comment"
ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Add Identity Protection Detection Comment"
)
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident"
ON_DEMAND_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - On Demand Scan"
RUN_SCRIPT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Run Script"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alert"
ADD_ALERT_COMMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Alert Comment"
GET_ALERT_DETAILS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Alert Details"
SEARCH_EVENTS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Search Events"
HIDE_HOST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Hide Hosts"

# CONNECTOR NAMES
ALERTS_CONNECTOR_NAME = f"{PROVIDER_NAME} Alerts Connector"
DETECTION_CONNECTOR_NAME = f"{PRODUCT_NAME} Detection Connector"
EVENT_STREAMING_CONNECTOR_NAME = f"{PROVIDER_NAME} Streaming Connector"
IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_NAME = f"{PROVIDER_NAME} Identity Protection Detections Connector"
INCIDENTS_CONNECTOR_NAME = f"{PRODUCT_NAME} Incidents Connector"

# JOB NAME
SYNC_ALERTS_JOB_NAME = f"{PRODUCT_NAME} Sync Alerts"

DEFAULT_PADDING_PERIOD = 1
MAX_PADDING_PERIOD = 6

DEFAULT_SEVERITY = 3
DETECTION_EVENT_TYPE = "DetectionSummaryEvent"
AUTH_ACTIVITY_AUDIT_EVENT_TYPE = "AuthActivityAuditEvent"
USER_ACTIVITY_AUDIT_EVENT_TYPE = "UserActivityAuditEvent"
REMOTE_RESPONSE_SESSION_START_EVENT_TYPE = "RemoteResponseSessionStartEvent"
REMOTE_RESPONSE_SESSION_END_EVENT_TYPE = "RemoteResponseSessionEndEvent"
SIEM_DETECTION_EVENT_TYPE = "Detection"
SIEM_AUTH_ACTIVITY_AUDIT_EVENT_TYPE = "AuthActivity"
SIEM_USER_ACTIVITY_AUDIT_EVENT_TYPE = "UserActivity"
SIEM_REMOTE_RESPONSE_SESSION_EVENT_TYPE = "Remote"

ADDITIONAL_TYPES_MAPPING = {
    SIEM_DETECTION_EVENT_TYPE: DETECTION_EVENT_TYPE,
    SIEM_AUTH_ACTIVITY_AUDIT_EVENT_TYPE: AUTH_ACTIVITY_AUDIT_EVENT_TYPE,
    SIEM_USER_ACTIVITY_AUDIT_EVENT_TYPE: USER_ACTIVITY_AUDIT_EVENT_TYPE,
    SIEM_REMOTE_RESPONSE_SESSION_EVENT_TYPE: [
        REMOTE_RESPONSE_SESSION_START_EVENT_TYPE,
        REMOTE_RESPONSE_SESSION_END_EVENT_TYPE,
    ],
}

SIEM_UNKNOWN_EVENT_TYPE = "Unknown"
STREAM_STARTED = "streamStarted"
STREAM_STOPPED = "streamStopped"
API_CLIENT_ID_KEY = "APIClientID"
APP_ID_KEY = "appId"
TIMEOUT_THRESHOLD = 0.9
DEFAULT_ALERT_NAME = "alert_with_no_behaviors"
DEFAULT_DEVICE_PRODUCT = "Falcon"
ENRICHMENT_PREFIX = "CrowdStrike"
MAX_RESULTS_FOR_CONTAIN_LOGIC = 1000
INFO_SEVERITY_NAME = "Info"

SEVERITIES = ["Low", "Medium", "High", "Critical"]

HOSTS = "hostnames"
IP_ADDRESSES = "ip_addresses"
URLS = "urls"
HASHES = "hashes"

# FILENAMES
OFFSET_FILE = "offset.json"

# KEYS
OFFSET_DB_KEY = "offset"
KEY_FOR_SAVED_OFFSET = "offset"

# ACTION TYPES
ACTION_TYPE_DETECT = "Detect"
ACTION_TYPE_BLOCK = "Block"
ACTION_TYPE_MAPPING = {ACTION_TYPE_BLOCK: "Prevent", ACTION_TYPE_DETECT: "Detect"}


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


OPEN = "open"
REOPEN = "reopened"
SEVERITY_POSSIBLE_VALUES = [
    Severity.CRITICAL.value,
    Severity.HIGH.value,
    Severity.MEDIUM.value,
    Severity.LOW.value,
    Severity.UNKNOWN.value,
]

API_ROOT_DEFAULT = "https://api.crowdstrike.com"


# TABLES NAMES
HOSTS_TABLE_NAME = "Hosts"
HOSTS_BY_IOC = "Devices Ran On - {}"
LIST_UPLOADED_IOCS = "Custom IOCs"

# INSIGHTS CONSTANTS
INSIGHT_KEYS = {EntityTypes.ADDRESS: "IP", EntityTypes.HOSTNAME: "Hostname"}

INSIGHT_VALUES = {EntityTypes.ADDRESS: "local_ip", EntityTypes.HOSTNAME: "hostname"}


class DetectionStatusEnum(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    IGNORED = "ignored"
    SELECT_ONE = "Select One"
    CLOSED = "closed"


class FilterStrategy(Enum):
    Equal = "Equal"
    Contains = "Contains"


FILTER_STRATEGY_MAPPING = {
    FilterStrategy.Equal.value: lambda item, value: str(item).lower() == str(value).lower(),
    FilterStrategy.Contains.value: lambda item, value: str(value).lower() in str(item).lower(),
}

ADDRESS = "ipv4"
DOMAIN = "domain"

TYPES_IOC_MAPPER = {
    EntityTypes.HOSTNAME: DOMAIN,
    EntityTypes.ADDRESS: ADDRESS,
    EntityTypes.URL: DOMAIN,
    EntityTypes.FILEHASH: "",
}
SUPPORTED_HASH_TYPES = ["md5", "sha256"]


class DeviceStatusEnum(Enum):
    NORMAL = "normal"
    CONTAINMENT_PENDING = "containment_pending"
    CONTAINED = "contained"
    LIFT_CONTAINMENT_PENDING = "lift_containment_pending"


IOC_DEFAULT_SEVERITY = "high"


IOC_PLATFORM_VALUES = ["Windows", "Linux", "Mac"]

STATUS_NORMAL = "normal"
STATE_ONLINE = "online"
STATE_OFFLINE: str = "offline"

PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"
CHARACTERS_LIMIT = 256

DEFAULT_MAX_LIMIT = 100

IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_DEFAULT_SEVERITY = "0"
IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_DEFAULT_MAX_HOURS_BACKWARDS = 1
IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_DEFAULT_LIMIT = 10

IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_PREFIX = "Crowdstrike_IDP_"
IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_DEVICE_VENDOR = "Crowdstrike"
IDENTITY_PROTECTION_DETECTIONS_CONNECTOR_DEVICE_PRODUCT = "Identity Protection"

ALERTS_CONNECTOR_MIN_SEVERITY = 0
ALERTS_CONNECTOR_MAX_SEVERITY = 100

ALERTS_CONNECTOR_PREFIX = "Crowdstrike_Alert_"
ALERTS_CONNECTOR_DEVICE_VENDOR = "Crowdstrike"
ALERTS_CONNECTOR_DEVICE_PRODUCT = "Alerts"
ALERTS_CONNECTOR_RULE_GENERATOR = "Crowdstrike Alert: {display_name}"


ALERTS_CONNECTOR_SEVERITY_MAPPING = {
    "critical": 80,
    "high": 60,
    "medium": 40,
    "low": 20,
    "info": 0,
    "informational": 0,
}
DEFAULT_FALLBACK_SEVERITY: str = "informational"

SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

DETECTION_STATUS_MAPPING = {
    "Select One": "",
    "Closed": "Closed",
    "In Progress": "In_progress",
    "New": "new",
    "Reopened": "reopened",
}

UNASSIGN = "Unassign"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
DEFAULT_TIMEOUT = 300

CID_ERROR = "only your own cid can be provided"
HOST_ERROR = "warning or invalid input"
FILE_TYPE_BAD_ERROR = "FILE_TYPE_BAD_ERROR"
SUCCESS_STATE = "success"
ERROR_STATE = "error"
RUNNING_STATE = "running"

ENVIRONMENTS = {
    "Linux Ubuntu 16.04, 64-bit": 300,
    "Android (static analysis)": 200,
    "Windows 10, 64-bit": 160,
    "Windows 7, 64-bit": 110,
    "Windows 7, 32-bit": 100,
}
NETWORKS = {
    "Default": "default",
    "TOR": "tor",
    "Simulated": "simulated",
    "Offline": "offline",
}

DEFAULT_ACTION_CONTEXT = """{
    "submissions": {},
    "failed_extractions": {}
}"""

INCIDENTS_CONNECTOR_DEFAULT_MAX_HOURS_BACKWARDS = "1"
INCIDENTS_CONNECTOR_DEFAULT_INCIDENTS_TO_FETCH = "10"
INCIDENTS_CONNECTOR_MIN_INCIDENTS_TO_FETCH = 1
INCIDENTS_CONNECTOR_MAX_INCIDENTS_TO_FETCH = 100
INCIDENTS_CONNECTOR_SEVERITY_MIN_VAL = 1
INCIDENTS_CONNECTOR_SEVERITY_MAX_VAL = 100

INCIDENTS_CONNECTOR_ALERT_DISPLAY_ID_PREFIX = "Crowdstrike_INC"
INCIDENTS_CONNECTOR_ALERT_DISPLAY_NAME_PREFIX = "Crowdstrike Incident"
INCIDENTS_CONNECTOR_RULE_GENERATOR_PREFIX = "Crowdstrike Incident"
INCIDENTS_CONNECTOR_DEVICE_VENDOR = "Crowdstrike"
INCIDENTS_CONNECTOR_DEVICE_PRODUCT = "Incidents"

INCIDENTS_CONNECTOR_SEVERITY_MAPPING = {
    "critical": 75,
    "high": 50,
    "medium": 25,
    "low": 1,
}

UPDATE_INCIDENT_STATUS_MAPPING = {
    "closed": "40",
    "in progress": "30",
    "new": "20",
    "reopened": "25",
}

UPDATE_INCIDENT_DEFAULT_STATUS = "select one"
UPDATE_INCIDENT_USER_UNASSIGN_CODE = "unassign"
MAX_RETRIES = 5
RETRY_INTERVAL = 10

ASYNC_TIMEOUT_THRESHOLD_IN_MS = 60_000
DEFAULT_MAX_SCAN_DURATION = 1
CPU_PRIORITY_MAPPING = {
    "Up to 1% CPU utilization": 1,
    "Up to 25% CPU utilization": 2,
    "Up to 50% CPU utilization": 3,
    "Up to 75% CPU utilization": 4,
    "Up to 100% CPU utilization": 5,
}
DETECTION_PREVENTION_MAPPING = {
    "Disabled": 0,
    "Cautious": 1,
    "Moderate": 2,
    "Aggressive": 3,
    "Extra Aggressive": 4,
}

DETECTION_LEVEL_PARAM_VALUES = [
    "Cautious",
    "Moderate",
    "Aggressive",
    "Extra Aggressive",
]

PREVENTION_LEVEL_PARAM_VALUES = [
    "Cautious",
    "Moderate",
    "Aggressive",
    "Extra Aggressive",
    "Disabled",
]

RUN_SCRIPT_COMMAND = "runscript -CloudFile={script_name}"
RUN_SCRIPT_RAW_COMMAND = "runscript -Raw=```{raw_script}```"


class ScanStatus(Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    RUNNING = "running"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    INITIATED = "initiated"
    STARTED = "started"
    CANCELED = "canceled"
    FAILED = "failed"


NON_ASCII_REGEX = r"[^\x00-\x7F]"

DDL_PARAM_DEFAULT_VALUE = "Select One"
STATUS_VALUES = [DDL_PARAM_DEFAULT_VALUE, "Closed", "In Progress", "New", "Reopened"]
VERDICT_MAPPING = {
    DDL_PARAM_DEFAULT_VALUE: "",
    "True Positive": "true_positive",
    "False Positive": "false_positive",
    "Ignored": "ignored",
}
COMMENT_CHAR_LENGTH_LIMIT = 1024

MIN_HOSTS_TO_FETCH = 1
MAX_HOSTS_TO_FETCH = 1000
DEFAULT_DEVICES_LIMIT = 500

MAX_PAGE_SIZE = 5000

MAX_IOCS_TO_FETCH = 500
IOC_INDICATORS_MAX_PAGE_SIZE = 2000
MAX_IOC_LIMIT = 50

DEFAULT_REPOSITORY_TO_SEARCH: str = "All"
DEFAULT_TIME_FRAME: str = "Last Hour"
SEARCH_EVENTS_DEFAULT_LIMIT: int = 50
SEARCH_EVENTS_MAX_LIMIT: int = 1000
SEARCH_EVENTS_MIN_LIMIT: int = 1
PAUSE_DURATION: int = 0

REPOSITORY_MAP: Mapping[str, str] = {
    "All": "search-all",
    "Falcon": "investigate_view",
    "Third Party": "third-party",
    "IT Automation": "falcon_for_it_view",
    "Forensics": "forensics_view",
}

TIMEFRAME_PRESETS: Mapping[str, timedelta] = {
    "Last Hour": timedelta(hours=1),
    "Last 6 Hours": timedelta(hours=6),
    "Last 24 Hours": timedelta(hours=24),
    "Last Week": timedelta(weeks=1),
    "Last Month": timedelta(days=30),
}
TIME_FRAME_CUSTOM: str = "Custom"

POSSIBLE_REPOSITORY_VALUES: list[str] = list(REPOSITORY_MAP.keys())
POSSIBLE_TIMEFRAME_VALUES: list[str] = [TIME_FRAME_CUSTOM] + list(TIMEFRAME_PRESETS.keys())


class EventStatus(Enum):
    IN_PROGRESS: str = "In Progress"
    COMPLETED: str = "Completed"
    CANCELLED: str = "Cancelled"


TimeRange = namedtuple("TimeRange", ["start_ts", "end_ts"])

LOCAL_IP_FILTER: str = "local_ip"
CONNECTION_IP_FILTER: str = "connection_ip"

ENTITIES_MAPPER: Mapping[str, list[str]] = {
    EntityTypes.ADDRESS: [LOCAL_IP_FILTER, CONNECTION_IP_FILTER],
    EntityTypes.HOSTNAME: ["starts_with_name"],
}
SYNC_ALERTS_CONTEXT_IDENTIFIER: str = "crowdstrike_sync_alerts"
SYNC_ALERTS_TIMEOUT_IN_MILLISECONDS: int = 600 * 1000
SECOPS_CASE_TAG: str = "Crowdstrike Alert"
ENTITY_TYPE: int = 2
CONTEXT_ALERT_ID_FIELD: str = "Alert_ID"
CROWDSTRIKE_COMMENT_PREFIX: str = "Crowdstrike "
COMMENTS_MODIFICATION_TIME_FILTER: int = 1
SECOPS_COMMENT_PREFIX: str = "Google SecOps "
ALERT_CLOSED_STATUS: str = "Closed"
CASES_SYNC_LIMIT: int = 10
CROWDSTRIKE_TRUE_POSITIVE: str = "true_positive"
CROWDSTRIKE_FALSE_POSITIVE: str = "false_positive"
CROWDSTRIKE_IGNORED: str = "ignored"
COMMENT_CHARACTER_LIMIT: int = 26
CROWDSTRIKE_COMPOSITE_ID_SEPARATOR: str = ":ind:"
CHUNK_SIZE: int = 100
