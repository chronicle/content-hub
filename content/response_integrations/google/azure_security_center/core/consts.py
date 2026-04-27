from __future__ import annotations
INTEGRATION_NAME = "Azure Security Center"
INTEGRATION_IDENTIFIER = "AzureSecurityCenter"

ENDPOINTS = {
    "get-auth-token": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    "ping": "https://management.azure.com/providers/Microsoft.Security/operations",
    "list-regulatory-standards": "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Security/regulatoryComplianceStandards/",
    "list-regulatory-standard-controls": "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Security/regulatoryComplianceStandards/{standard_name}/regulatoryComplianceControls",
    "update-alert-status": "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Security/locations/{location}/alerts/{alert_id}/{status}",
    "get-alert-ids": "https://graph.microsoft.com/v1.0/security/alerts",
    "get-alert-details": "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Security/locations/{location}/alerts/{alert_id}",
    "get-regulatory-compliance-standards": "https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.Security/regulatoryComplianceStandards/",
}

MICROSOFT_SECURITY_CENTER_SCOPE = "https://management.azure.com/.default"
MICROSOFT_GRAPH_SCOPE = "https://graph.microsoft.com/.default"
OAUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/token"

PING_SCRIPT_NAME = "Ping"
LIST_REGULATORY_STANDARDS_SCRIPT_NAME = "List Regulatory Standards"
LIST_REGULATORY_STANDARD_CONTROLS_SCRIPT_NAME = "List Regulatory Standard Controls"
UPDATE_ALERT_STATUS_SCRIPT_NAME = "Update Alert Status"
GET_AUTHORIZATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get OAuth Authorization Code"
GENERATE_TOKEN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get OAuth Refresh Token"
TOKEN_RENEWAL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Refresh Token Renewal Job"
DEFAULT_ALERT_STATUS = "Resolve"
DEFAULT_NUM_STANDARDS_TO_RETURN = 50

REGULATORY_STANDARD_STATES = ["passed", "failed", "unsupported", "skipped"]

MAPPED_ALERT_STATUS = {
    "Dismiss": "dismiss",
    "Reactivate": "activate",
    "Resolve": "resolve",
}

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

CONNECTOR_NAME = "Azure Security Center - Security Alerts Connector "
VENDOR = "Microsoft"
PRODUCT = "Azure Security Center"
HOURS_LIMIT_IN_IDS_FILE = 72
PAGE_SIZE = 100
DEFAULT_CONNECTOR_SCRIPT_EXECUTION_TIME = 180
MAX_EVENTS_PER_ALERT = 200
DEFAULT_MAX_ALERTS_TO_FETCH = 50
DEFAULT_MAX_HOURS_BACKWARDS = 1
DEFAULT_LOWEST_SEVERITY_TO_FETCH = "Low"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"

SEVERITIES_MAP = {
    "Low": ["low", "medium", "high"],
    "Medium": ["medium", "high"],
    "High": ["high"],
}

SIEMPLIFY_SEVERITIES = {
    "info": -1,
    "low": 40,
    "medium": 60,
    "high": 80,
    "critical": 100,
}

PLURAL_ALERT_STATUS = {
    "Dismiss": "dismissed",
    "Reactivate": "reactivated",
    "Resolve": "resolved",
}
ALERT_ID_KEY = "id"
