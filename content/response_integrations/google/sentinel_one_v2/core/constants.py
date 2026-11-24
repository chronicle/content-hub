from __future__ import annotations
INTEGRATION_NAME = "SentinelOneV2"
PRODUCT_NAME = "SentinelOne"


QUERY_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT = 50
DEFAULT_BLACK_LIST_LIMIT = 50
MAX_BLACK_LIST_LIMIT = 1000

MIN_AGENTS_TO_RETURN: int = 1
MAX_AGENTS_TO_RETURN: int = 1000

DEEP_VISIBILITY_QUERY_FINISHED = "FINISHED"
ENRICH_PREFIX = "SENO"
SENTINEL_PREFIX = "SENO_"
THREAT_MITIGATED_STATUS = "mitigated"
THREAT_TRUE_POSITIVE = "true_positive"

COMPLETED_QUERY_STATUSES = [
    "FAILED",
    "FINISHED",
    "ERROR",
    "QUERY_CANCELLED",
    "TIMED_OUT",
]
FAILED_QUERY_STATUSES = ["FAILED", "ERROR", "QUERY_CANCELLED", "TIMED_OUT"]


# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Ping'}"
GET_SYSTEM_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get System Status'}"
GET_SYSTEM_VERSION_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get System Version'}"
CREATE_HASH_BLACKLIST_RECORD_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Create Hash Blacklist Record'}"
)
CREATE_HASH_EXCLUSION_RECORD_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Create Hash Exclusion Record'}"
)
MITIGATE_THREAT_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Mitigate Threat'}"
DISCONNECT_AGENT_FROM_NETWORK_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Disconnect Agent From Network'}"
)
ENRICH_ENDPOINTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Enrich Endpoints'}"
RECONNECT_AGENT_TO_THE_NETWORK_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Reconnect Agent To The Network'}"
)
RESOLVE_THREAT_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Resolve Threat'}"
MARK_AS_THREAT_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Mark As Threat'}"
CREATE_PATH_EXCLUSION_RECORD_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Create Path Exclusion Record'}"
)
GET_THREATS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Threats'}"
INITIATE_FULL_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Initiate Full Scan'}"
INITIATE_DEEP_VISIBILITY_QUERY_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Initiate Deep Visibility Query'}"
)
MOVE_AGENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Move Agents'}"
GET_APPLICATION_LIST_FOR_ENDPOINT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Get Applications List For Endpoints'}"
)
GET_AGENT_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Agent Status'}"
GET_SITE_AGENTS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - {'Get Site Agents'}"
GET_BLACK_LIST_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Blacklist'}"
GET_DEEP_VISIBILITY_QUERY_RESULT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Get Deep Visibility Query Result'}"
)
UPDATE_INCIDENT_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Update Incident Status'}"
GET_GROUP_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Group Details'}"
GET_HASH_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Hash Reputation'}"
GET_EVENTS_FOR_ENDPOINT_HOURS_BACK_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Get Events For Endpoint Hours Back'}"
)
DOWNLOAD_THREAT_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Download Threat File'}"
UPDATE_ANALYST_VERDICT_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Update Analyst Verdict'}"
ADD_THREAT_NOTE_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Add Threat Note'}"
REMOVE_HASH_BLACKLIST_RECORD_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Delete Hash Blacklist Record'}"
)
LIST_SITES_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'List Sites'}"
UPDATE_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - {'Update Alert'}"
ALERTS_CONNECTOR_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - {'Alerts Connector'}"
CREATE_DEVICE_CONTROL_RULE_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - {'Create Device Control Rule'}"
)
UPDATE_DEVICE_CONTROL_RULE_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - {'Update Device Control Rule'}"
)
DELETE_DEVICE_CONTROL_RULE_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - {'Delete Device Control Rule'}"
)

# TABLES NAMES
SYSTEM_VERSION_TABLE_NAME = "System Version"
UNSUCCESSFUL_ATTEMPTS_TABLE_NAME = "Unsuccessful Attempts"
AGENT_STATUSES_TABLE_NAME = "Agents Statuses"
THREATS_TABLE_NAME = "Sentinel One - Threats"
BLACKLIST_HASHES_TABLE_NAME = "Blacklist Hashes"
SENTINEL_ONE_EVENTS_TABLE_NAME = "SentinelOne Events"
SENTINEL_ONE_GROUPS_TABLE_NAME = "SentinelOne Groups"
FOUND_EVENTS_TABLE_NAME = "Found {} Events for {}"


MODE_MAPPER = {
    "Suppress Alerts": "suppress",
    "Interoperability": "disable_in_process_monitor",
    "Interoperability - Extended": "disable_in_process_monitor_deep",
    "Performance Focus": "disable_all_monitors",
    "Performance Focus - Extended": "disable_all_monitors_deep",
}

ACTIVE_STATUS_VALUE = "Active"
NOT_ACTIVE_STATUS_VALUE = "Not Active"

KILL = "kill"
QUARANTINE = "quarantine"
UN_QUARANTINE = "un-quarantine"
REMEDIATE = "remediate"
ROLLBACK_REMEDIATION = "rollback-remediation"

MITIGATION_MAPPING = {
    KILL: "kill",
    QUARANTINE: "quarantine",
    UN_QUARANTINE: "un-quarantine",
    REMEDIATE: "remediate",
    ROLLBACK_REMEDIATION: "rollback-remediation",
}

AFFECTED_STATUS = 1
ACTIVITY_TYPE = 86

FALSE_POSITIVE = "False Positive"
TRUE_POSITIVE = "True Positive"
SUSPICIOUS = "Suspicious"
UNDEFINED = "Undefined"

ANALYST_VERDICT_MAPPING = {
    FALSE_POSITIVE: "false_positive",
    TRUE_POSITIVE: "true_positive",
    SUSPICIOUS: "suspicious",
    UNDEFINED: "undefined",
}

INCIDENT_STATUS_MAPPING = {
    "Unresolved": "unresolved",
    "In Progress": "in_progress",
    "Resolved": "resolved",
}

SHA1_LENGTH = 40
DEFAULT_GET_BLACKLIST_ITEM_LIMIT = 1
FILTER_KEY_MAPPING = {"Select One": "", "Name": "name", "ID": "id"}

FILTER_STRATEGY_MAPPING = {
    "Not Specified": "",
    "Equal": lambda item, value: str(item).lower() == str(value).lower(),
    "Contains": lambda item, value: str(value).lower() in str(item).lower(),
}

SELECT_ONE: str = "Select One"
SEVERITIES: list[str] = ["Info", "Low", "Medium", "High", "Critical"]

SEVERITIES_FILTER_MAPPING: dict[str, str] = {
    "INFO": ",".join(SEVERITIES[0:]),
    "LOW": ",".join(SEVERITIES[1:]),
    "MEDIUM": ",".join(SEVERITIES[2:]),
    "HIGH": ",".join(SEVERITIES[3:]),
    "CRITICAL": ",".join(SEVERITIES[4:]),
}

ALERTS_CONNECTOR_SEVERITY_MAPPING: dict[str, int] = {
    "critical": 80,
    "high": 60,
    "medium": 40,
    "low": 20,
    "info": 0,
}
SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

TIMEOUT_THRESHOLD: float = 0.9

PLACEHOLDER_START: str = "["
PLACEHOLDER_END: str = "]"
DATE_TIME_FORMAT_UTC: str = "%Y-%m-%dT%H:%M:%SZ"
MAX_ALERTS_TO_FETCH: int = 100
DEFAULT_VENDOR: str = "SentinelOne"
DEFAULT_PRODUCT: str = "Alerts"

STATUS_FILTER_MAPPER: dict[str, str] = {
    "unresolved": "UNRESOLVED",
    "in progress": "IN_PROGRESS",
    "resolved": "RESOLVED",
}

STORED_IDS_LIMIT: int = 1000

SCOPE_TYPE_MAPPER: dict[str, str] = {
    "Account": "accountIds",
    "Group": "groupIds",
    "Site": "siteIds",
}
SCOPE_TYPE_DDL_VALUES: list[str] = list(SCOPE_TYPE_MAPPER.keys())

SYNC_THREATS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Threats"
THREATS_ENTITY_TYPE: int = 2
SYNC_THREATS_IDENTIFIER: str = "sentinelonev2_syncthreats"
THREAT_IDS_FILE_NAME: str = "sync_threats_ids.json"
SENTINELONE_THREAT_TAG: str = "SentinelOne Threat"
THREATS_SENTINELONE_COMMENT_PREFIX: str = "SentinelOne "
THREATS_SECOPS_COMMENT_PREFIX: str = "Google SecOps "
THREAT_ID_CONTEXT_KEY: str = "Threat_ID"
REASON_RESOLVED: str = "Inconclusive"
VERDICT_TRUE_POSITIVE: str = "true_positive"
VERDICT_FALSE_POSITIVE: str = "false_positive"
VERDICT_INCONCLUSIVE: str = "inconclusive"
THREAT_STATUS_RESOLVED: str = "resolved"
THREAT_STATUS_ACTIVE: str = "active"
REASON_MALICIOUS: str = "Malicious"
REASON_NOT_MALICIOUS: str = "NotMalicious"
REASON_INCONCLUSIVE: str = "Inconclusive"
THREATS_CASE_STATUS: str = "BOTH"
THREATS_INCREMENT_CASE_UPDATED_TIME_BY_MS: int = 1
THREATS_CASES_SYNC_LIMIT: int = 10
THREATS_ALERTS_LIMIT: int = 30
BATCH_SIZE: int = 50
SYNC_THREATS_TIMEOUT_IN_MILLISECONDS: int = 600 * 1000
THREATS_COMMENTS_MODIFICATION_TIME_FILTER: int = 1
SYNC_COMMENTS_OFFSET_BUFFER_MS: int = 1800000
MIN_THREAT_ID_LENGTH: int = 18
ALERT_CLOSE_STATUS: str = "Close"
MAX_TIMESTAMP_SECONDS: int = 100_000_000_000
MILLISECONDS_FACTOR: float = 1000.0
ACTIVITY_TYPE_INCIDENT_STATUS_CHANGE: int = 2028
ACTIVITY_TYPE_ANALYST_VERDICT_CHANGE: int = 2030
ACTIVITY_TYPE_NOTE_ADDED: int = 4020
ACTIVITY_NOTE_ACTION_ADDED: str = "added"

# SyncAlerts Job
SYNC_ALERTS_JOB_NAME = f"{PRODUCT_NAME} Sync Alerts"
SYNC_ALERTS_CONTEXT_IDENTIFIER: str = "sentinelone_sync_alerts"
SYNC_ALERTS_TIMEOUT_IN_MILLISECONDS: int = 280000
SECOPS_CASE_TAG: str = "SentinelOne Alert"
CASE_STATUS: str = "BOTH"
ENTITY_TYPE: int = 2
ALERT_ID_CONTEXT_PROPERTY = "Alert_ID"
COMMENTS_MODIFICATION_TIME_FILTER: int = 1
SECOPS_COMMENT_PREFIX: str = "Google SecOps: "
ALERTS_LIMIT: int = 30
SENTINELONE_COMMENTS_LIMIT: int = 40
CASES_SYNC_LIMIT: int = 10
SENTINELONE_TRUE_POSITIVE: str = "true_positive"
SENTINELONE_FALSE_POSITIVE: str = "false_positive"
SENTINELONE_IGNORED: str = "ignored"
SENTINELONE_COMMENT_PREFIX: str = "SentinelOne: "
MIN_ALERT_ID_LENGTH: int = 18
INCREMENT_CASE_UPDATED_TIME_BY_MS: int = 1
SENTINELONE_RESOLVED: str = "resolved"
REASON_MALICIOUS: str = "Malicious"
REASON_NOT_MALICIOUS: str = "NotMalicious"
REASON_INCONCLUSIVE: str = "Inconclusive"
ALERT_CLOSED_STATUS: str = "Close"
FETCH_ALERTS_CHUNK_SIZE: int = 50
MAX_RETRIES: int = 3
RETRY_BACKOFF_FACTOR: int = 2
RETRY_INITIAL_DELAY: int = 1
INITIAL_ATTEMPT: int = 0
