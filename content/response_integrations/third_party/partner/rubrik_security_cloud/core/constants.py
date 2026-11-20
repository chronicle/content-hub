from __future__ import annotations

INTEGRATION_NAME = "Rubrik Security Cloud"
INTEGRATION_VERSION = "1.0.0"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
DEFAULT_DEVICE_VENDOR = "Rubrik"
DEFAULT_DEVICE_PRODUCT = INTEGRATION_NAME
RULE_GENERATOR = DEFAULT_DEVICE_VENDOR
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
DEFAULT_PAGE_SIZE = 1000
RETRY_COUNT = 3
WAIT_TIME_FOR_RETRY = 5
DEFAULT_RESULTS_LIMIT = 10000000
RATE_LIMIT_EXCEEDED_STATUS_CODE = 429
UNAUTHORIZED_STATUS_CODE = 401
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_OFFSET = "0"
DEFAULT_LIMIT = "100"
MAX_TABLE_RECORDS: int = 1000
MAX_JSON_CHARS = 300
MAX_INT_VALUE = 65535
DEFAULT_REQUEST_NAME = "GoogleSecOps"
DEFAULT_SCAN_NAME = "Google-SecOps-{DATE}-{TIME}"
MAX_SNAPSHOTS_LIMIT = 1000
DEFAULT_TIMEZONE = "UTC"
DEFAULT_SNAPSHOTS_SORT_TYPE = "ASC"
DEFAULT_SONAR_FILE_SORT_ORDER = "DESC"
INTERNAL_SERVER_ERROR_STATUS_CODES = [500, 502, 503, 504]
LIST_EVENTS_DEFAULT_SORT_BY = "LAST_UPDATED"
LIST_EVENTS_DEFAULT_SORT_ORDER = "DESC"
DEFAULT_SEARCH_TIME_PERIOD = "7"
TOKEN_EXPIRY_BUFFER_SECONDS = 30  # 30 seconds buffer
DEFAULT_EXPIRY_SECONDS = 1800 - TOKEN_EXPIRY_BUFFER_SECONDS  # 30 minutes
EXPIRES_IN_KEY = "expires_in"

# Time formats
UNIX_FORMAT = "unix"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Script Names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
TURBO_IOC_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Turbo IOC Scan"
ADVANCE_IOC_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Advanced IOC Scan"
IOC_SCAN_RESULTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - IOC Scan Results"
LIST_OBJECT_SNAPSHOTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Object-Snapshots"
LIST_SONAR_FILE_CONTEXTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Sonar File Contexts"
LIST_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Events"
GET_CDM_CLUSTER_LOCATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get CDM Cluster Location"
GET_CDM_CLUSTER_CONNECTION_STATE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get CDM Cluster Connection State"
)
GET_SONAR_SENSITIVE_HITS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Sonar Sensitive Hits"
SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Search DSPM Violations"
GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get DSPM Violation Details"
UPDATE_VIOLATION_STATUS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Update Violation Status"
DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Download Snapshot Results CSV"
DOWNLOAD_REMEDIATION_LOG_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Download Remediation Log"
GET_VIOLATION_FILE_LIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Violation File List"
SEARCH_IR_VIOLATIONS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Search IR Violations"
GET_IR_VIOLATION_DETAILS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get IR Violation Details"

# API Endpoints
FILE_DOWNLOAD_ENDPOINT: str = "/file-downloads/{external_id}"

# Token TTL (seconds) — 12 hours
TOKEN_TTL_SECONDS: int = 43200

# Default pagination limits
DEFAULT_MAX_RESULTS: int = 50
DEFAULT_FILE_LIST_MAX_RESULTS: int = 25
MAX_ALLOWED_RESULTS: int = 1000

# Maximum violations and files to return
MAX_VIOLATIONS: int = 1000
MAX_FILES: int = 1000

# HTTP Headers
USER_AGENT_NAME: str = "GoogleSecOps"

# File types for async downloads
USER_FILE_TYPE_CSV: str = "SNAPSHOT_RESULTS_CSV"
USER_FILE_TYPE_LOG: str = "REMEDIATION_ACTIONS_LOG_CSV"

# File filter types
FILE_TYPE_HITS: str = "HITS"
ACCESS_TYPE_UNSPECIFIED: str = "ACCESS_TYPE_UNSPECIFIED"

# Connector Constants
CONNECTOR_VERSION: str = "2026-07-31-v1"
CONNECTOR_NAME: str = "Rubrik - Fetch DSPM Classification and IR Violations"
MAX_CONNECTOR_RESULTS: int = 100
TEST_MODE_MAX_RESULTS: int = 10
EVENTS_PAGE_SIZE: int = 1000
CLASSIFICATION_ACTIVITY_MESSAGE_FILTER: str = (
    "Results available in the Objects page for the workload"
)

# Fixed template text RSC uses for the audit entry it mints when the
# remediation log or snapshot results CSV is downloaded against a violation's
# activity series (see RubrikActivityViolationAlertDatamodel.get_latest_activity_node).
# Anchored on this phrase rather than "downloaded" alone, since the policy name
# is interpolated into the same message and a policy named e.g. "Files
# downloaded externally" would otherwise be misidentified as audit noise.
ACTIONS_LOG_DOWNLOAD_MESSAGE_PREFIX: str = "Actions log for object"

# RSC fetch types — which sources the connector ingests. These are internal
# identifiers rather than API enums; the connector routes each fetched activity
# series to one of them and skips the types that were not selected.
RSC_FETCH_TYPE_CLASSIFICATION: str = "CLASSIFICATION"
RSC_FETCH_TYPE_DSPM: str = "DSPM"
RSC_FETCH_TYPE_IR: str = "IR"
RSC_FETCH_TYPE_ENUM_MAP: dict[str, str] = {
    "Classification": RSC_FETCH_TYPE_CLASSIFICATION,
    "DSPM": RSC_FETCH_TYPE_DSPM,
    "IR": RSC_FETCH_TYPE_IR,
}
ERROR_NO_RSC_FETCH_TYPES: str = (
    "'RSC Fetch Types' is required. Select at least one of: {}."
)

# activitySeriesConnection is the single source for all three fetch types. Its
# activityConnection holds one immutable entry per lifecycle transition, each
# with a stable id -- unlike policyViolations, whose lastUpdatedAt is bumped by
# RSC's own periodic re-evaluation of unchanged records, so a re-touch there
# produced a fresh alert every hour. Polling activity series instead means a
# no-op re-touch mints no new entry and therefore raises no alert.
ACTIVITY_STATUS_SUCCESS: str = "SUCCESS"
# Sort direction for the sweep. Every page is walked until hasNextPage is false,
# so this does not affect which series are returned -- only the order they
# arrive in.
ACTIVITY_SWEEP_SORT_ORDER: str = "DESC"
ACTIVITY_TYPE_CLASSIFICATION: str = "CLASSIFICATION"
ACTIVITY_TYPE_SECURITY_VIOLATION: str = "SECURITY_VIOLATION"
ACTIVITY_TYPE_IDENTITY_VIOLATION: str = "IDENTITY_VIOLATION"
ACTIVITY_TYPE_IDENTITY_ALERTS: str = "IDENTITY_ALERTS"

# Which lastActivityType values each fetch type covers. IR spans two activity
# types; DSPM's data-security findings arrive as SECURITY_VIOLATION.
RSC_FETCH_TYPE_ACTIVITY_TYPES: dict[str, list[str]] = {
    RSC_FETCH_TYPE_CLASSIFICATION: [ACTIVITY_TYPE_CLASSIFICATION],
    RSC_FETCH_TYPE_DSPM: [ACTIVITY_TYPE_SECURITY_VIOLATION],
    RSC_FETCH_TYPE_IR: [
        ACTIVITY_TYPE_IDENTITY_VIOLATION,
        ACTIVITY_TYPE_IDENTITY_ALERTS,
    ],
}

# Reverse lookup used to route a fetched series back to its fetch type. Keys are
# upper-cased because RSC echoes lastActivityType back in its own casing
# ("Classification") rather than the filter's ("CLASSIFICATION").
ACTIVITY_TYPE_TO_FETCH_TYPE: dict[str, str] = {
    activity_type.upper(): fetch_type
    for fetch_type, activity_types in RSC_FETCH_TYPE_ACTIVITY_TYPES.items()
    for activity_type in activity_types
}

# The violation's lifecycle status, exactly as RSC returns it on the
# policyViolation record the connector looks up per activity series. This enum is
# the ONLY status the connector writes -- it lands on the event as `status`,
# unmodified, and is the single field playbooks and the Close Duplicate Violation
# Alerts Job branch on.
#
# The connector used to also parse a bare-word status out of the activity message
# ("... was remediated" -> REMEDIATED) and ingest it as violationStatus. That was
# removed: it duplicated `status` on the case wall in a second spelling. An alert
# whose lookup returns nothing now carries no status at all, and the job leaves
# that violation open instead of guessing from message wording.
#
# Shared with the job -- both sides must agree on these exact strings, so neither
# may hardcode its own copy.
POLICY_VIOLATION_STATUS_OPEN: str = "POLICY_VIOLATION_STATUS_OPEN"
POLICY_VIOLATION_STATUS_IN_PROGRESS: str = "POLICY_VIOLATION_STATUS_IN_PROGRESS"
POLICY_VIOLATION_STATUS_REMEDIATED: str = "POLICY_VIOLATION_STATUS_REMEDIATED"
POLICY_VIOLATION_STATUS_CLOSED: str = "POLICY_VIOLATION_STATUS_CLOSED"
POLICY_VIOLATION_STATUS_DISMISSED: str = "POLICY_VIOLATION_STATUS_DISMISSED"

# Statuses that mean the violation is finished; anything else -- including a
# missing status -- leaves it, and therefore its case, open.
TERMINAL_POLICY_VIOLATION_STATUSES: set[str] = {
    POLICY_VIOLATION_STATUS_REMEDIATED,
    POLICY_VIOLATION_STATUS_CLOSED,
    POLICY_VIOLATION_STATUS_DISMISSED,
}

# Fields a usable RSC service account JSON must carry. Validated up front by the
# connector so a malformed credential fails with a message naming the parameter,
# before any filter parsing or API call is attempted.
SERVICE_ACCOUNT_REQUIRED_KEYS: tuple[str, ...] = ("client_id", "client_secret", "access_token_uri")
ERROR_SERVICE_ACCOUNT_MISSING_KEYS: str = (
    "'Service Account JSON' is missing required field(s): {}. "
    "Provide the full service account JSON downloaded from RSC."
)

# eventName written into ingested classification events, used by the "Event Field
# Name" (EventClassId) connector setting. DSPM and IR use their series'
# lastActivityType verbatim instead of a constructed label.
CLASSIFICATION_ALERT_EVENT_NAME: str = "ClassficationResultsAvailable"

# Alert name templates for DSPM / IR. Composed rather than taken from the RSC
# activity message: severity and policy_name are parsed out of the message (the
# only place activitySeriesConnection exposes them), while target is the series'
# own objectName field. RSC rewords the message on each lifecycle transition
# ("... detected on 'X'" vs "... on 'X' was remediated") and may name a different
# target in the process, so composing keeps one violation's name stable across
# its whole lifecycle.
#
# DSPM and IR violations (severity rendered in title case):
#   "Critical severity violation of policy 'Publicly accessible sensitive data'
#    detected on 'Admin'"
ALERT_NAME_VIOLATION_TEMPLATE: str = (
    "{severity} severity violation of policy '{policy_name}' detected on '{target}'"
)
# IR identity events — no severity prefix:
#   "'Member was removed from a privileged group' detected on 'fuji.us'"
ALERT_NAME_IDENTITY_EVENT_TEMPLATE: str = "'{policy_name}' detected on '{target}'"
# Classification — snapshot time is trimmed out of the activity message:
#   "Data security violations found for workload 'ran test' on the snapshot at
#    Friday 19-Jun-26 20:01 UTC"
ALERT_NAME_CLASSIFICATION_TEMPLATE: str = (
    "Data security violations found for workload '{object_name}' "
    "on the snapshot at {snapshot_time}"
)
UNKNOWN_LABEL: str = "Unknown"

# Search time period (days) bounds for the connector. The window must be between
# 0 and 1 day; a negative or larger value raises.
MIN_SEARCH_TIME_PERIOD_DAYS: int = 0
MAX_SEARCH_TIME_PERIOD_DAYS: int = 1

# Checkpoint file (persisted in the connector run folder) storing only the
# {from_timestamp} the next run should start from.

# Severity Mapping (Rubrik severity → SOAR priority score). WARNING is the
# activity-series severity RSC reports alongside the violation severities.
RUBRIK_SEVERITY_MAP: dict[str, int] = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "WARNING": 60,
    "LOW": 40,
    "INFO": 20,
    "NO": 20,
}

# Action Identifiers
PING_ACTION_IDENTIFIER = "ping"
TURBO_IOC_SCAN_ACTION_IDENTIFIER = "turbo_ioc_scan"
ADVANCE_IOC_SCAN_ACTION_IDENTIFIER = "advance_ioc_scan"
IOC_SCAN_RESULTS_ACTION_IDENTIFIER = "ioc_scan_results"
LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER = "list_object_snapshots"
LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER = "list_sonar_file_contexts"
LIST_EVENTS_ACTION_IDENTIFIER = "list_events"
GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER = "get_cdm_cluster_location"
GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER = "get_cdm_cluster_connection_state"
GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER = "get_sonar_sensitive_hits"
GET_CLASSIFICATION_OBJECT_DETAIL_ACTION_IDENTIFIER: str = "get_classification_object_detail"
GET_SNAPPABLE_IDENTITY_ACTION_IDENTIFIER: str = "get_snappable_identity"

# GraphQL URL
GRAPHQL_URL = "https://{domain}/api/graphql"

# IOC type mapping from UI dropdown/JSON keys to Rubrik GraphQL iocKind values
IOC_TYPE_MAP = {
    "INDICATOR_OF_COMPROMISE_TYPE_HASH": "IOC_HASH",
    "INDICATOR_OF_COMPROMISE_TYPE_PATH_OR_FILENAME": "IOC_FILE_PATTERN",
    "INDICATOR_OF_COMPROMISE_TYPE_YARA_RULE": "IOC_YARA",
    # Also allow direct GraphQL kinds if passed in JSON
    "IOC_HASH": "IOC_HASH",
    "IOC_PATH_OR_FILENAME": "IOC_FILE_PATTERN",
    "IOC_YARA_RULE": "IOC_YARA",
}

# ENUM Lists
SORT_ORDER_ENUM = ["ASC", "DESC"]


# Status Enum Mapping (UI label → API value)
STATUS_ENUM_MAP: dict[str, str] = {
    "Open": "POLICY_VIOLATION_STATUS_OPEN",
    "In Progress": "POLICY_VIOLATION_STATUS_IN_PROGRESS",
    "Remediated": "POLICY_VIOLATION_STATUS_REMEDIATED",
    "Dismissed": "POLICY_VIOLATION_STATUS_DISMISSED",
    "Closed": "POLICY_VIOLATION_STATUS_CLOSED",
}

# Severity Enum Mapping
DSPM_SEVERITY_MAP: dict[str, str] = {
    "Low": "LOW",
    "Medium": "MEDIUM",
    "High": "HIGH",
    "Critical": "CRITICAL",
}

# DSPM Category Enum Mapping
DSPM_CATEGORY_MAP: dict[str, str] = {
    "Misplaced": "MISPLACED",
    "Redundant": "REDUNDANT",
    "Overexposed": "OVEREXPOSED",
    "Unprotected": "UNPROTECTED",
}

# Sensitivity Level Enum Mapping
SENSITIVITY_LEVEL_MAP: dict[str, str] = {
    "High Sensitivity": "HIGH_SENSITIVITY",
    "Medium Sensitivity": "MEDIUM_SENSITIVITY",
    "Low Sensitivity": "LOW_SENSITIVITY",
    "No Sensitivity": "NO_SENSITIVITY",
}

# DSPM Sort By Enum Mapping
DSPM_SORT_BY_MAP: dict[str, str] = {
    "Detection Time": "SORT_DETECTION_TIME",
    "Update Time": "SORT_UPDATE_TIME",
    "Severity": "SORT_SEVERITY",
    "Hits": "SORT_HITS",
    "Files At Risk": "SORT_FILES_AT_RISK",
    "Name": "SORT_NAME",
    "Status": "SORT_STATUS",
}

# IR Sort By Enum Mapping
IR_SORT_BY_MAP: dict[str, str] = {
    "Detection Time": "SORT_DETECTION_TIME",
    "Update Time": "SORT_UPDATE_TIME",
    "Severity": "SORT_SEVERITY",
    "Name": "SORT_NAME",
    "Status": "SORT_STATUS",
    "Identity Type": "SORT_IDENTITY_TYPE",
}

# Sort Order Enum Mapping
SORT_ORDER_MAP: dict[str, str] = {
    "Ascending": "ASC",
    "Descending": "DESC",
}

# IR Policy Types Enum Mapping
IR_POLICY_TYPE_MAP: dict[str, str] = {
    "Identity": "POLICY_TYPE_IDENTITY",
    "IDP": "POLICY_TYPE_IDP",
    "Identity Event": "POLICY_TYPE_IDENTITY_EVENT",
}

# Every IR policy type, sent when the connector looks an IR violation up by id:
# the details query requires policyTypes, and the activity series does not say
# which one applies, so all three are passed and RSC resolves it.
ALL_IR_POLICY_TYPES: list[str] = list(IR_POLICY_TYPE_MAP.values())

# IR Category Enum Mapping
IR_CATEGORY_MAP: dict[str, str] = {
    "Identity Hygiene": "IDENTITY_HYGIENE",
    "Authentication and Secret Management": "AUTHENTICATION_AND_SECRET_MANAGEMENT",
    "Identity Provider Security": "IDENTITY_PROVIDER_SECURITY",
    "Excessive Identity Rights": "EXCESSIVE_IDENTITY_RIGHTS",
}

# IR Identity Provider Enum Mapping
IR_IDENTITY_PROVIDER_ENUM_MAP: dict[str, str] = {
    "Unspecified": "IDP_UNSPECIFIED",
    "On-Prem AD": "ON_PREM_AD",
    "Entra ID": "ENTRA_ID",
    "AWS": "AWS",
    "Local AD": "LOCAL_AD",
    "SharePoint": "SHAREPOINT",
    "System": "SYSTEM",
    "Okta": "OKTA",
}

# IR Identity Tag Enum Mapping
IR_IDENTITY_TAG_ENUM_MAP: dict[str, str] = {
    "Unspecified": "IDENTITY_TAG_UNSPECIFIED",
    "Privileged": "PRIVILEGED",
    "At Risk": "AT_RISK",
    "Sensitive": "SENSITIVE",
}

# File List Risk Level Enum Mapping
FILE_RISK_LEVEL_MAP: dict[str, str] = {
    "Unknown Risk": "UNKNOWN_RISK",
    "High Risk": "HIGH_RISK",
    "Medium Risk": "MEDIUM_RISK",
    "Low Risk": "LOW_RISK",
    "No Risk": "NO_RISK",
}

# File List Exposure Enum Mapping
FILE_EXPOSURE_MAP: dict[str, str] = {
    "Explicit": "EXPLICIT",
    "Inherited": "INHERITED",
    "Not Open": "NOT_OPEN",
    "Unknown Access": "UNKNOWN_ACCESS",
    "Public": "PUBLIC",
}

# File List Access Via Enum Mapping
FILE_ACCESS_VIA_MAP: dict[str, str] = {
    "Unspecified": "ACCESS_TYPE_UNSPECIFIED",
    "Direct": "DIRECT",
    "Group": "GROUP",
    "Role": "ROLE",
}

# File List Sort By Enum Mapping
FILE_SORT_BY_MAP: dict[str, str] = {
    "Hits": "HITS",
    "Name": "NAME",
    "Last Access Time": "LAST_ACCESS_TIME",
    "Last Modified": "LAST_MODIFIED",
    "Creation Time": "CREATION_TIME",
    "Last Scan Time": "LAST_SCAN_TIME",
}

# Remediation type for log export
REMEDIATION_TYPE_EXPORT_LOG: str = "REMEDIATION_TYPE_EXPORT_ACTIONS_LOG_TO_CSV"
REMEDIATION_TARGET_TYPE_VIOLATION: str = "REMEDIATION_TARGET_TYPE_VIOLATION"

# File states (polling)
FILE_STATE_READY: str = "READY"
FILE_STATE_FAILED: str = "FAILED"


# Default IR policy types
DEFAULT_IR_POLICY_TYPES: list[str] = ["POLICY_TYPE_IDENTITY", "POLICY_TYPE_IDP"]

# Error Messages
ERROR_NO_VIOLATION_FOUND: str = "No violation found with ID: {}"
ERROR_INVALID_ENUM: str = "Invalid value '{}' for parameter '{}'. Valid values: {}"
ERROR_DETECTION_DATE_ORDER: str = "Detection End Date must be later than Detection Start Date."
ERROR_UPDATE_DATE_ORDER: str = "Update End Date must be later than Update Start Date."

# Get Violation File List date-order messages
ERROR_LAST_ACCESS_DATE_ORDER: str = "Last Access End Date must be later than Last Access Start Date."
ERROR_LAST_UPDATED_DATE_ORDER: str = "Last Updated End Date must be later than Last Updated Start Date."
ERROR_CREATION_DATE_ORDER: str = "Creation End Date must be later than Creation Start Date."
ERROR_LAST_SCAN_DATE_ORDER: str = "Last Scan End Date must be later than Last Scan Start Date."

# DSPM Object Type Enum Mapping (values are used verbatim as the API enum)
DSPM_OBJECT_TYPE_VALUES: list[str] = [
    "VSPHERE_VIRTUAL_MACHINE",
    "LINUX_FILESET",
    "SHARE_FILESET",
    "NUTANIX_VIRTUAL_MACHINE",
    "WINDOWS_FILESET",
    "HYPERV_VIRTUAL_MACHINE",
    "VOLUME_GROUP",
    "NAS_FILESET",
    "AZURE_VIRTUAL_MACHINE",
    "AZURE_MANAGED_DISK",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_SQL_DATABASE_DB",
    "AZURE_SQL_MANAGED_INSTANCE_DB",
    "O365_ONEDRIVE",
    "O365_SITE",
    "AWS_NATIVE_S3_BUCKET",
    "AWS_NATIVE_EBS_VOLUME",
    "AWS_NATIVE_RDS_INSTANCE",
    "AWS_NATIVE_DYNAMODB_TABLE",
    "ORACLE_DATABASE",
    "ORACLE_DATA_GUARD_GROUP",
    "K8S_VIRTUAL_MACHINE",
    "GCP_NATIVE_DISK",
    "GCP_NATIVE_GCE_INSTANCE",
    "K8S_PROTECTION_SET",
]
DSPM_OBJECT_TYPE_ENUM_MAP: dict[str, str] = {value: value for value in DSPM_OBJECT_TYPE_VALUES}

# ── Close Duplicate Violation Alerts Job ─────────────────────────────────────
CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Close Duplicate Violation Alerts Job"
)

MS_PER_DAY: int = 24 * 60 * 60 * 1000

# Hard ceiling on how many candidate open case IDs are fetched from SOAR in
# Step 1, independent of the "Max Cases To Process" job param -- see
# _validate_job_params for how the two interact.
FETCH_MAX_RESULTS: int = 10000

# Hard ceiling on "Lookback Days" -- large values don't change how many cases
# are fetched (still capped at FETCH_MAX_RESULTS), but they do make Step 1's
# SOAR query scan a much wider case history for no benefit, contributing to
# the same processing-timeout risk as an oversized "Max Cases To Process".
MAX_LOOKBACK_DAYS: int = 100

# Job-scoped context key the checkpoint is persisted under -- same key naming
# convention as CASES_TIMESTAMP_DB_KEY in the Vectra RUX "Expire Inactive
# Detections" job, which uses the identical get/set_scoped_job_context_property
# checkpoint pattern this job now mirrors.
CASES_TIMESTAMP_DB_KEY: str = "cases_timestamp"
