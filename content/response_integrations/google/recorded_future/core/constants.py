from __future__ import annotations
PROVIDER_NAME = "RecordedFuture"
DEFAULT_DEVICE_VENDOR = "Recorded Future"

# Actions name
PING_SCRIPT_NAME = "Ping"
ENRICH_CVE_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich CVE"
ENRICH_HASH_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich Hash"
ENRICH_HOST_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich Host"
ENRICH_IP_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich IP"
ENRICH_URL_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich URL"
ENRICH_IOC_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich IOC"
GET_ALERT_DETAILS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Alert Details"
GET_CVE_RELATED_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Get CVE Related Entities"
GET_HASH_RELATED_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Hash Related Entities"
GET_HOST_RELATED_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Host Related Entities"
GET_IP_RELATED_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Ip Related Entities"
ADD_ANALYST_NOTE_SCRIPT_NAME = f"{PROVIDER_NAME} - Add Analyst Note"
UPDATE_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Update Alert"

# Connector
CONNECTOR_NAME = "Recorded Future - Security Alerts Connector"
DEFAULT_TIME_FRAME = 0
CONNECTOR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DEFAULT_LIMIT = 100
SEVERITY_MAP = {"Low": 40, "Medium": 60, "High": 80, "Critical": 100}
STORED_IDS_LIMIT = 3000
ALERT_ID_FIELD = "id"

DEFAULT_THRESHOLD = 25
DEFAULT_SCORE = 0
SUPPORTED_ENTITY_TYPES_ENRICHMENT = ["URL", "ADDRESS", "FILEHASH", "CVE", "HOSTNAME"]
SUPPORTED_ENTITY_TYPES_RELATED_ENTITIES = ["ADDRESS", "FILEHASH", "CVE", "HOSTNAME"]
ENRICHMENT_DATA_PREFIX = "RF"

TOPIC_MAP = {
    "None": "",
    "Actor Profile": "TXSFt2",
    "Analyst On-Demand Report": "VlIhvH",
    "Cyber Threat Analysis": "TXSFt1",
    "Flash Report": "TXSFt0",
    "Indicator": "TXSFt4",
    "Informational": "UrMRnT",
    "Malware/Tool Profile": "UX0YlU",
    "Source Profile": "UZmDut",
    "Threat Lead": "TXSFt3",
    "Validated Intelligence Event": "TXSFt5",
    "Weekly Threat Landscape": "VlIhvG",
    "YARA Rule": "VTrvnW",
}

ALERT_STATUS_MAP = {
    "Unassigned": "unassigned",
    "Assigned": "assigned",
    "Pending": "pending",
    "Dismissed": "dismiss",
    "New": "no-action",
    "Resolved": "actionable",
    "Flag for Tuning": "tuning",
    "Select One": None,
}
