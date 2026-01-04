from __future__ import annotations

INTEGRATION_NAME = "SpyCloud"
INTEGRATION_DISPLAY_NAME = "SpyCloud"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_CATALOGS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Catalogs"
LIST_ENTITY_BREACHES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Entity Breaches"

ENDPOINTS = {
    "ping": "/enterprise-v1/breach/catalog/1",
    "get_catalogs": "/enterprise-v1/breach/catalog",
    "get_breaches": "/enterprise-v1/breach/data/{breach_type}/{breach_identifier}",
}

TIMEFRAME_MAPPING = {
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Last Year": "last_year",
    "Custom": "custom",
}

EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
DEFAULT_LIMIT = 1
DEFAULT_CATALOGS_LIMIT = 50

IPS_BREACH_TYPE = "ips"
EMAILS_BREACH_TYPE = "emails"
DOMAINS_BREACH_TYPE = "domains"
USERNAMES_BREACH_TYPE = "usernames"
