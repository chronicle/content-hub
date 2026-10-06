"""Shared constants for the Flare - Google SecOps integration."""
from __future__ import annotations

INTEGRATION_NAME = "flare_secops"
DEVICE_PRODUCT = "Flare"
PRODUCT_NAME = "Flare-IO"
# Distinct marker so SOAR alerts can be verified as connector-sourced.
# Also used as AlertInfo.rule_generator for closed-case remediation lookup.
VENDOR_NAME = "Flare"

# Action script names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SYNC_REMEDIATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Remediation"

# Connector
THREAT_FINDINGS_CONNECTOR_NAME = "Flare Connector"
CHECKPOINT_PROPERTY_KEY = "flare_ingestion_checkpoint"
REMEDIATION_PROPERTY_KEY = "flare_remediation_state"

# Flare API endpoints
ENDPOINT_EVENTS_SEARCH = "/firework/v4/events/tenant/_search"
ENDPOINT_EVENTS_DETAIL = "/firework/v4/events/"
ENDPOINT_EVENT_ACTIONS = "/firework/v4/events/actions"
ENDPOINT_FILTER_SEVERITIES = "/firework/v4/events/filters/severities"
ENDPOINT_FILTER_TYPES = "/firework/v4/events/filters/types"
ENDPOINT_TENANTS = "/firework/v2/me/tenants"

DEFAULT_FLARE_API_URL = "https://api.flare.io"
DEFAULT_FLARE_ACTION_BATCH_SIZE = 10
DEFAULT_FLARE_PAGE_SIZE = 10
MAX_BACKFILL_RANGE_DAYS = 180
MAX_FLARE_PAGE_SIZE = 10
MAX_EVENTS_PER_ALERT = 500
SEVERITY_OPTIONS = ("info", "low", "medium", "high", "critical")
SEVERITY_TO_ALERT_PRIORITY = {
    "critical": 100,
    "high": 80,
    "medium": 60,
    "low": 40,
    "info": 20,
}
TYPE_DISPLAY_NAME = {
    "paste": "Paste site exposure",
    "chat_message": "Chat message exposure",
    "driller": "Source code exposure",
    "service": "Exposed service",
    "forum_post": "Hacker forum post",
    "forum_content": "Hacker forum content",
    "listing": "Dark web marketplace listing",
    "blog_post": "Threat blog post",
    "blog_content": "Threat blog content",
    "bot": "Stealer log / bot exposure",
    "leaked_credential": "Leaked credential",
    "valid_credential": "Valid leaked credential",
    "invalid_credential": "Invalid leaked credential",
    "mitigated_credential": "Mitigated leaked credential",
    "ransomleak": "Ransomware leak",
    "infected_devices": "Infected device",
    "financial_data": "Financial data exposure",
    "social_media": "Social media exposure",
    "source_code": "Source code exposure",
    "buckets": "Cloud bucket exposure",
    "leak": "Data leak",
    "profile": "Profile exposure",
}

# HTTP status codes
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403
NOT_FOUND = 404
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500
