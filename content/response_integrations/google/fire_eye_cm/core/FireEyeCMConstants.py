from __future__ import annotations
PROVIDER_NAME = "FireEye CM"
DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye CM"

# CONNECTORS
ALERTS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Alerts Connector"
ALERT_ID_FIELD = "uuid"
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
DURATION = "48_hours"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f-00:00"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
ADD_IOC_FEED_SCRIPT_NAME = f"{PROVIDER_NAME} - Add IOC Feed"
ACKNOWLEDGE_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Acknowledge Alert"
LIST_QUARANTINED_EMAILS_SCRIPT_NAME = f"{PROVIDER_NAME} - List Quarantined Emails"
RELEASE_QUARANTINED_EMAIL_SCRIPT_NAME = f"{PROVIDER_NAME} - Release Quarantined Email"
DELETE_QUARANTINED_EMAIL_SCRIPT_NAME = f"{PROVIDER_NAME} - Delete Quarantined Email"
DOWNLOAD_QUARANTINED_EMAIL_SCRIPT_NAME = f"{PROVIDER_NAME} - Download Quarantined Email"
LIST_IOC_FEEDS_SCRIPT_NAME = f"{PROVIDER_NAME} - List IOC Feeds"
DELETE_IOC_FEED_SCRIPT_NAME = f"{PROVIDER_NAME} - Delete IOC Feed"
DOWNLOAD_ALERT_ARTIFACTS_SCRIPT_NAME = f"{PROVIDER_NAME} - Download Alert Artifacts"
ADD_RULE_TO_CUSTOM_RULES_FILE_SCRIPT_NAME = (
    f"{PROVIDER_NAME} - Add Rule To Custom Rules Files"
)
DOWNLOAD_CUSTOM_RULES_FILE_SCRIPT_NAME = f"{PROVIDER_NAME} - Download Custom Rules File"

# SIEM
FIREEYE_CM_TO_SIEM_SEVERITY = {"MINR": 60, "MAJR": 80, "CRIT": 100}

ENDPOINTS = {
    "authorize": "wsapis/v2.0.0/auth/login",
    "get_system_config": "wsapis/v2.0.0/config",
    "logout": "wsapis/v2.0.0/auth/logout",
    "test_connectivity": "wsapis/v2.0.0/health/system",
    "download_artifacts": "wsapis/v2.0.0/artifacts/{alert_uuid}",
    "get_alerts": "wsapis/v2.0.0/alerts",
    "add_ioc_feed": "wsapis/v2.0.0/customioc/feed/add",
    "acknowledge_alert": "wsapis/v2.0.0/alerts/alert/{alert_uuid}",
    "list_quarantined_emails": "wsapis/v2.0.0/emailmgmt/quarantine",
    "release_quarantined_email": "wsapis/v2.0.0/emailmgmt/quarantine/release",
    "delete_quarantined_email": "wsapis/v2.0.0/emailmgmt/quarantine/delete",
    "download_quarantined_email": "wsapis/v2.0.0/emailmgmt/quarantine/{queue_id}",
    "list_ioc_feeds": "wsapis/v2.0.0/customioc/feed",
    "delete_ioc_feed": "wsapis/v2.0.0/customioc/feed/delete/{feed_name}",
    "download_alert_artifacts": "wsapis/v2.0.0/artifacts/{alert_uuid}",
    "download_custom_rules_file": "wsapis/v2.0.0/customioc/snort",
    "upload_custom_rules_file": "wsapis/v2.0.0/customioc/snort/add/custom",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# Entities mapping
IP_TYPE = "IP"
URL_TYPE = "URL"
MD5_TYPE = "MD5"
SHA256_TYPE = "SHA256"
DOMAIN_TYPE = "Domain"

SHA256_LENGTH = 64
MD5_LENGTH = 32

FEED_TYPE_MAPPING = {
    IP_TYPE: "ip",
    URL_TYPE: "url",
    MD5_TYPE: "hash_md5",
    SHA256_TYPE: "hash_sha256",
    DOMAIN_TYPE: "domain",
}

IOC_FEED_CONTENT_TYPE_CSV_MAPPING = {
    "ip": "IP",
    "url": "URL",
    "domain": "Domain",
    "hash": "Hash",
}

ACTION_TYPE_MAPPING = {"Alert": "alert", "Block": "block"}
ENTITIES_FILE_NAME = "Siemplify_temp_{}_feed.txt"
FEED_NAME = "Siemplify_{}"

DEFAULT_MAX_EMAILS_TO_RETURN = 50
MAX_EMAILS_TO_RETURN = 10000
MIN_EMAILS_TO_RETURN = 1

DEFAULT_MAX_IOC_FEEDS_TO_RETURN = 50
MIN_IOC_FEEDS_TO_RETURN = 1

# API Status Codes
API_NOT_FOUND = 404
API_BAD_REQUEST = 400
INTERNAL_SERVER_ERROR = 500

EX_APPLIANCE_TYPE = "eMPS"
NX_APPLIANCE_TYPE = "wMPS"

EX_APPLIANCE_NAME = "FireEye EX"
NX_APPLIANCE_NAME = "FireEye NX"

DOWNLOADED_QUARANTINED_EMAIL_FILE_NAME = "Quarantined_email_{}.eml"
TEMP_CUSTOM_RULES_FILE_NAME = "Siemplify_temp_{}_custom_rules.txt"
DOWNLOADED_CUSTOM_RULES_FILE_NAME = "Siemplify_custom_rules_file.txt"
DOWNLOADED_ALERT_ARTIFACTS = "Alert_Artifacts_{}.zip"
