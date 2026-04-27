from __future__ import annotations
PROVIDER_NAME = "Office 365 Management API"
MANAGE_API_ROOT = "https://manage.office.com/api/v1.0/"
GRANT_TYPE = "client_credentials"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

ENDPOINTS = {
    "get_token": "{directory_id}/oauth2/token?api-version=1.0",
    "start_subscription": "{directory_id}.onmicrosoft.com/activity/feed/subscriptions/start?contentType={content_type}",
    "stop_subscription": "{directory_id}.onmicrosoft.com/activity/feed/subscriptions/stop?contentType={content_type}",
    "get_data_blobs": "api/v1.0/{directory_id}/activity/feed/subscriptions/content",
}

DEVICE_VENDOR = "Microsoft"
DEVICE_PRODUCT = "Office 365 Management API"

HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

# Actions
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
START_SUBSCRIPTION_SCRIPT_NAME = f"{PROVIDER_NAME} - Start Subscription"
STOP_SUBSCRIPTION_SCRIPT_NAME = f"{PROVIDER_NAME} - Stop Subscription"

# Connector
CONNECTOR_NAME = "Office 365 Management API DLP Events Connector"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 0
UNIX_FORMAT = 1
DATETIME_FORMAT = 2
DEFAULT_LIMIT = 100
CONNECTOR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
SEVERITY_MAP = {"Low": 40, "Medium": 60, "High": 80}
AUDIT_GENERAL_SEVERITY_MAP = {
    "Informational": -1,
    "Low": 40,
    "Medium": 60,
    "High": 80,
    "Critical": 100,
}


PARAMETERS_DEFAULT_DELIMITER = ","

ALERT_TYPES = {"dlp": "DLP", "audit_general": "Audit.General"}

ALERT_CONTENT_TYPE = {
    ALERT_TYPES["dlp"]: "DLP.All",
    ALERT_TYPES["audit_general"]: "Audit.General",
}
